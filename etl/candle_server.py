#!/usr/bin/env python3
"""Loopback on-demand candle helper for the 8777 cockpit (no CGI; http.server can't exec).

The page (stock.html / sepa.html) cannot exec Python from a static server, so it POSTs
the code here; this spawns the existing fetchers (Fugle intraday + FinMind daily if the
daily file is missing) with the FUGLE key sourced from a local .env (never in html/Pages).

  POST /fetch  {"code":"2454","tfs":["5","15","60"]}   -> 202 {started, daily_missing}
  GET  /status?code=2454                              -> {code, fresh:{5,15,60}, daily:{n,asof}}

Bind: 127.0.0.1 only. No keys in responses. Never writes data/fundflo.
"""
from __future__ import annotations
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path("/Users/lin/Downloads/tw-moneyflow-viz")
OUT = ROOT / "data" / "candles"
ENV = Path.home() / "trading-workspace" / ".env"
LOG = Path("/tmp/candle_helper.log")
PORT = int(os.environ.get("CANDLE_PORT", "8790"))
STALE_MS = 180_000  # 3 min
LOCK = Path("/tmp/candle_helper.lock")
P2_LOCK = Path("/tmp/cockpit_p2.lock")
LLM_URL = os.environ.get("COCKPIT_LLM_URL", "http://192.168.31.151:8888/v1").rstrip("/")
LIVE_DIR = ROOT / "data" / "live"
LIVE_LOCK = Path("/tmp/live_scan.lock")
LIVE_DEDUP = Path("/tmp/live_dedup.json")
SECTOR_MAP = ROOT / "etl" / "tw_industry_map.json"
NOTIFY_STATE = Path("/tmp/live_notified.json")


def log(msg: str) -> None:
    try:
        with LOG.open("a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%F %T')} {msg}\n")
    except Exception:
        pass


def load_key() -> str:
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8").splitlines():
            if line.startswith("FUGLE_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get("FUGLE_API_KEY", "")


def file_age_ms(p: Path) -> int:
    if not p.exists():
        return 0
    return int((time.time() - p.stat().st_mtime) * 1000)


def is_fresh(p: Path) -> bool:
    a = file_age_ms(p)
    return a > 0 and a <= STALE_MS


# ---------- WAVE 3 D4 P1: 長期記憶 (small JSON memory layer) ----------
MEM_DIR = ROOT / "data" / "memory"
MEM_SYMBOLS = MEM_DIR / "symbols"


def _mem_user_path() -> Path:
    return MEM_DIR / "user.json"


def _mem_symbol_path(code: str) -> Path:
    return MEM_SYMBOLS / f"{str(code).zfill(4)}.json"


def _read_json_safe(p: Path):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def memory_context(code: str) -> dict:
    """Injectable memory block for /ask and /p2. Never contains secrets.
    Missing files -> empty (assistant still works)."""
    out = {"present": False, "user": None, "symbol": None}
    u = _read_json_safe(_mem_user_path())
    s = _read_json_safe(_mem_symbol_path(code)) if code else None
    if u is not None:
        out["user"] = u
        out["present"] = True
    if s is not None:
        out["symbol"] = s
        out["present"] = True
    return out


def memory_render(code: str) -> str:
    """Compact text block appended to an LLM prompt. Empty string if none."""
    mc = memory_context(code)
    if not mc["present"]:
        return ""
    lines = ["[長期記憶 — 本機 user/symbol JSON，供上下文引用，非新聞]"]
    u = mc["user"] or {}
    if u:
        pref = u.get("risk_pref")
        rules = u.get("rules") or []
        notes = u.get("watch_notes") or []
        if pref:
            lines.append(f"- 風險偏好: {pref}")
        if notes:
            lines.append(f"- 觀察備註: {('; '.join(str(n) for n in notes))[:300]}")
        if rules:
            lines.append(f"- 規則: {('; '.join(str(r) for r in rules))[:300]}")
    s = mc["symbol"] or {}
    if s:
        tk = s.get("last_takeaway")
        lo = s.get("levels_of_interest") or []
        un = s.get("user_notes") or []
        if tk:
            lines.append(f"- {code} 上次結論: {str(tk)[:300]}")
        if lo:
            lines.append(f"- {code} 關注位: {('; '.join(str(x) for x in lo))[:300]}")
        if un:
            lines.append(f"- {code} 用戶筆記: {('; '.join(str(x) for x in un))[:300]}")
    return "\n".join(lines)


def _env() -> dict:
    e = dict(os.environ)
    key = load_key()
    if key:
        e["FUGLE_API_KEY"] = key
    return e


def daily_state(code: str) -> dict:
    p = OUT / f"{code}.json"
    if not p.exists():
        return {"present": False, "n": 0, "asof": None}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        daily = d.get("daily") or []
        return {"present": True, "n": len(daily), "asof": daily[-1]["time"] if daily else None}
    except Exception:
        return {"present": True, "n": 0, "asof": None}


def tf_state(code: str, tf: str) -> dict:
    _f = {"5": "5m", "15": "15m", "60": "1h"}.get(str(tf), str(tf) + "m")
    p = OUT / f"{code}_{_f}.json"
    return {"present": p.exists(), "fresh": is_fresh(p), "age_ms": file_age_ms(p)}


def _closes_since(code: str, as_of: str) -> list:
    """Daily closes strictly after as_of (the frozen date)."""
    p = OUT / f"{code}.json"
    if not as_of or not p.exists():
        return []
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return [b["close"] for b in (d.get("daily") or []) if b.get("time", "") > as_of]
    except Exception:
        return []


def score_outcome(row: dict, closes: list) -> dict:
    """Port of kansoku HistoryTab outcomes: hit_target/hit_stop/held_range/broke_range/open.
    direction from weights_pct argmax; anchor = pivot (fallback base)."""
    scn = row.get("scenarios") or {}
    bull, bear, base = scn.get("bull"), scn.get("bear"), scn.get("base")
    w = row.get("weights_pct") or {}
    if w.get("bear", 0) > w.get("bull", 0) and w.get("bear", 0) >= w.get("base", 0):
        direction = "short"
    elif w.get("bull", 0) > w.get("bear", 0) and w.get("bull", 0) >= w.get("base", 0):
        direction = "long"
    else:
        direction = "neutral"
    anchor = row.get("pivot") or base
    if not closes or not anchor:
        return {"direction": direction, "anchor": anchor, "status": "open", "pct": None,
                "last": None}
    last = closes[-1]
    pct = (last - anchor) / anchor * 100 if anchor else None
    if bull and last >= bull:
        status = "hit_target"
    elif bear and last <= bear:
        status = "hit_stop" if direction == "long" else "hit_target"
    elif direction == "long" and base and last < base:
        status = "broke_range"
    elif direction == "short" and base and last > base:
        status = "broke_range"
    else:
        status = "held_range"
    return {"direction": direction, "anchor": anchor, "status": status,
            "pct": round(pct, 2) if pct is not None else None, "last": last}


def history_rows(code: str) -> list:
    """All frozen rows for a code, newest first, each with a live outcome score."""
    rows = []
    try:
        for line in (ROOT / "data" / "cockpit" / "cockpit.jsonl").read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            r = json.loads(line)
            if str(r.get("code", "")).zfill(4) == code:
                rows.append(r)
    except Exception:
        return []
    out = []
    for r in rows:
        closes = _closes_since(code, r.get("as_of"))
        o = score_outcome(r, closes)
        out.append({"as_of": r.get("as_of"), "created_at": r.get("created_at"),
                    "scenarios": r.get("scenarios"), "weights_pct": r.get("weights_pct"),
                    "pivot": r.get("pivot"), "outcome": o})
    out.reverse()
    return out


def recap_rows(limit: int = 12) -> list:
    """#19 RecapBoard: yesterday's frozen setups across codes, scored vs latest bar."""
    from datetime import datetime, timedelta, timezone
    tpe = timezone(timedelta(hours=8))
    today = datetime.now(tpe).strftime("%Y-%m-%d")
    rows = []
    try:
        for line in (ROOT / "data" / "cockpit" / "cockpit.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    except Exception:
        return []
    out = []
    best = {}
    for r in rows:
        code = str(r.get("code", "")).zfill(4)
        if not code or not r.get("as_of") or r.get("as_of") >= today:
            continue
        prev = best.get(code)
        if not prev or r.get("as_of") > prev.get("as_of"):
            best[code] = r
    for code, r in best.items():
        closes = _closes_since(code, r.get("as_of"))
        o = score_outcome(r, closes)
        # intraday close (latest 5m) as a fresher 'last' if no next-day daily yet
        last5 = None
        try:
            d = json.loads((OUT / f"{code}_5m.json").read_text(encoding="utf-8"))
            bars = (d.get("timeframes", {}).get("5m") or {}).get("bars", [])
            if bars:
                last5 = bars[-1].get("close")
        except Exception:
            pass
        if o["last"] is None and last5 is not None:
            o["last"] = last5
            if o["anchor"]:
                o["pct"] = round((last5 - o["anchor"]) / o["anchor"] * 100, 2)
        out.append({"code": code, "as_of": r.get("as_of"),
                    "scenarios": r.get("scenarios"), "outcome": o})
    out.sort(key=lambda x: (x["outcome"].get("pct") is None, x["outcome"].get("pct") or 0))
    return out[:limit]


FOLLOW_DIR = ROOT / "data" / "cockpit"


def follow_path(code: str) -> Path:
    return FOLLOW_DIR / f"follow_{code}.json"


def follow_state(code: str) -> dict:
    p = follow_path(code)
    if not p.exists():
        return {"following": False, "code": code}
    try:
        st = json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"following": False, "code": code}
    # live trigger check on latest 5m close
    trig = None
    try:
        d = json.loads((OUT / f"{code}_5m.json").read_text(encoding="utf-8"))
        bars = (d.get("timeframes", {}).get("5m") or {}).get("bars", [])
        if bars:
            last = bars[-1].get("close")
            if last is not None:
                st["last"] = last
                if st.get("target") and st.get("entry") and st.get("stop"):
                    up = st["entry"] < st["target"]
                    if up and (last >= st["target"] or last <= st["stop"]):
                        trig = "target" if last >= st["target"] else "stop"
                    elif not up and (last <= st["target"] or last >= st["stop"]):
                        trig = "target" if last <= st["target"] else "stop"
                if trig and not st.get("triggered"):
                    st["triggered"] = True
                    st["trigger_at"] = bars[-1].get("time")
    except Exception:
        pass
    st["following"] = True
    st["trigger"] = trig
    return st



# ---------- INTRADAY LIVE WATCH (5m hunter) ----------
def _sma_last(vals, n):
    if len(vals) < n:
        return None
    return sum(vals[-n:]) / n


def _last_cross(series):
    """Return 'up'/'down' if series crossed zero on its last bar, else None."""
    if len(series) < 2:
        return None
    a, b = series[-2], series[-1]
    if a is None or b is None:
        return None
    if a >= 0 > b:
        return "down"
    if a <= 0 < b:
        return "up"
    return None


def load_finmind_token() -> str:
    def valid(s: str) -> bool:
        s = s.strip()
        return len(s) >= 20 and sum(c.isalnum() for c in s) / max(len(s), 1) >= 0.8
    if ENV.exists():
        for line in ENV.read_text(encoding="utf-8").splitlines():
            if line.startswith("FINMIND_TOKEN="):
                t = line.split("=", 1)[1].strip().strip('"').strip("'")
                if valid(t):
                    return t
    t = os.environ.get("FINMIND_TOKEN", "")
    return t if valid(t) else ""


NEWS_DIR = ROOT / "data" / "news"


def _tpe_today():
    from datetime import datetime, timedelta, timezone
    return datetime.now(timezone(timedelta(hours=8)))


def fetch_news_finmind(code: str, date: str = None) -> list:
    """FinMind 日股新聞 (dataset=TaiwanStockNews, one day per call).
    date=YYYY-MM-DD TPE; default today, walk back up to 7 weekdays.
    Returns items [{time,title,url,source,date}] newest-first."""
    import urllib.parse
    import urllib.request
    tok = load_finmind_token()
    if not tok:
        raise RuntimeError("FINMIND_TOKEN missing")
    tpe = _tpe_today()
    days = []
    if date:
        days.append(date)
    else:
        d = tpe
        while len(days) < 7:
            if d.weekday() < 5:
                days.append(d.strftime("%Y-%m-%d"))
            d -= timedelta(days=1)
    items = []
    for day in days:
        q = urllib.parse.urlencode({"dataset": "TaiwanStockNews", "data_id": code,
                                   "start_date": day, "end_date": day})
        req = urllib.request.Request(
            "https://api.finmindtrade.com/api/v4/data?" + q,
            headers={"Authorization": f"Bearer {tok}", "Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as r:
            out = json.loads(r.read().decode())
        if out.get("status") != 200:
            continue
        for x in out.get("data") or []:
            items.append({"time": str(x.get("date") or day), "title": x.get("title") or "",
                          "url": x.get("link") or "", "source": x.get("source") or "",
                          "date": day})
        if items:
            break  # one day of news is enough; don't hammer the free API
    items.sort(key=lambda i: i.get("time") or "", reverse=True)
    return items


def news_state(code: str) -> dict:
    p = NEWS_DIR / f"{code}.json"
    if not p.exists():
        return {"present": False, "n": 0, "asof": None}
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        return {"present": True, "n": len(d.get("items") or []), "asof": d.get("asof")}
    except Exception:
        return {"present": False, "n": 0, "asof": None}


def run_news(code: str, refresh: bool = False) -> dict:
    NEWS_DIR.mkdir(parents=True, exist_ok=True)
    p = NEWS_DIR / f"{code}.json"
    if not refresh and p.exists() and file_age_ms(p) <= 6 * 3600 * 1000:
        d = json.loads(p.read_text(encoding="utf-8"))
        return {"ok": True, "cached": True, "code": code, "items": d.get("items") or []}
    try:
        items = fetch_news_finmind(code)
    except Exception as e:
        # fallback: keep stale cache if any
        if p.exists():
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                return {"ok": True, "cached": True, "stale": True, "code": code,
                        "items": d.get("items") or [], "error": str(e)}
            except Exception:
                pass
        return {"ok": False, "error": f"FinMind 新聞抓取失敗: {type(e).__name__}: {e}"}
    if items:
        (NEWS_DIR / f"{code}.json").write_text(
            json.dumps({"code": code, "asof": _tpe_today().strftime("%Y-%m-%d"), "items": items},
                       ensure_ascii=False), encoding="utf-8")
        log(f"news {code} n={len(items)}")
    return {"ok": True, "code": code, "items": items}


def live_watchlist() -> list:
    """Union of FundFlo top codes + recent cockpit codes + anchors; cap 60 (documented)."""
    out = []
    seen = set()

    def add(c):
        c = str(c).zfill(4)
        if c and c not in seen:
            seen.add(c)
            out.append(c)

    try:
        ff = json.loads((ROOT / "data" / "fundflo" / "latest.json").read_text(encoding="utf-8"))
        for s in (ff.get("stocks") or [])[:40]:
            add(s.get("code"))
    except Exception:
        pass
    try:
        for line in (ROOT / "data" / "cockpit" / "cockpit.jsonl").read_text(encoding="utf-8").splitlines()[-20:]:
            if line.strip():
                add(json.loads(line).get("code"))
    except Exception:
        pass
    for c in ("0050", "2330", "2317", "2454"):
        add(c)
    return out[:60]


def _load_dedup() -> dict:
    try:
        return json.loads(LIVE_DEDUP.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_dedup(d: dict) -> None:
    # keep last 5000 keys, prune old
    for k in [k for k in d if d[k] < time.time() - 6 * 3600]:
        d.pop(k, None)
    if len(d) > 5000:
        d = dict(list(d.items())[-5000:])
    LIVE_DEDUP.write_text(json.dumps(d), encoding="utf-8")


def live_scan(force_refresh: bool = True) -> dict:
    """Poll watchlist 5m bars (cached; refresh if stale in-session), fire rules, append jsonl."""
    LIVE_DIR.mkdir(parents=True, exist_ok=True)
    if not LIVE_LOCK.exists():
        LIVE_LOCK.write_text(str(os.getpid()))
    elif int(LIVE_LOCK.read_text() or 0) == os.getpid():
        pass
    else:
        other = int(LIVE_LOCK.read_text() or 0)
        try:
            os.kill(other, 0)
            return {"ok": False, "error": "another scan running", "pid": other}
        except OSError:
            pass
        LIVE_LOCK.write_text(str(os.getpid()))

    try:
        # TW session in UTC+8
        from datetime import datetime, timedelta, timezone
        tpe = timezone(timedelta(hours=8))
        now = datetime.now(tpe)
        tod = now.strftime("%H%M")
        if now.weekday() >= 5:
            in_session, session = False, "weekend"
        elif "0900" <= tod < "1130" or "1300" <= tod < "1330":
            in_session, session = True, "regular"
        elif "1130" <= tod < "1300":
            in_session, session = False, "lunch"
        elif tod < "0900":
            in_session, session = False, "pre"
        else:
            in_session, session = False, "after"

        # watchlist + names + industry
        wl = live_watchlist()
        names, industry = {}, {}
        try:
            ff = json.loads((ROOT / "data" / "fundflo" / "latest.json").read_text(encoding="utf-8"))
            for s in ff.get("stocks") or []:
                names[str(s.get("code")).zfill(4)] = s.get("name") or ""
        except Exception:
            pass
        try:
            industry = json.loads(SECTOR_MAP.read_text(encoding="utf-8"))
        except Exception:
            industry = {}

        # jsonl of frozen triggers
        frozen = {}
        try:
            for line in (ROOT / "data" / "cockpit" / "cockpit.jsonl").read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                r = json.loads(line)
                if r.get("code"):
                    frozen[str(r["code"]).zfill(4)] = r.get("scenarios") or {}
        except Exception:
            pass

        # 0050 5m closes for RS rule
        idx50 = []
        try:
            d50 = json.loads((OUT / "0050_5m.json").read_text(encoding="utf-8"))
            idx50 = [b["close"] for b in (d50.get("timeframes", {}).get("5m") or {}).get("bars", [])]
        except Exception:
            pass

        dedup = _load_dedup()
        events = []
        fired_codes = {}  # industry -> [codes] for sector heat

        for code in wl:
            p5 = OUT / f"{code}_5m.json"
            if not p5.exists():
                if in_session and force_refresh:
                    try:
                        subprocess.run([sys.executable, "etl/fetch_fugle_candles.py", "--code", code,
                                        "--timeframes", "5", "--days", "1", "--sleep", "0.2"],
                                       cwd=ROOT, env=_env(), timeout=25,
                                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    except Exception:
                        pass
                continue
            try:
                d = json.loads(p5.read_text(encoding="utf-8"))
                bars = (d.get("timeframes", {}).get("5m") or {}).get("bars", [])
            except Exception:
                continue
            if len(bars) < 25:
                continue
            b = bars[-1]
            C = [x["close"] for x in bars]
            V = [x.get("volume") or 0 for x in bars]
            ma20 = _sma_last(C, 20)
            ma60 = _sma_last(C, 60)
            vol20 = _sma_last(V, 20)
            ts = b.get("time") or 0
            name = names.get(code, "")
            ind = industry.get(code, "未分組")

            def fire(kind, detail, refs, severity):
                key = f"{code}:{kind}:{ts}"
                if dedup.get(key, 0) > 0:
                    return
                dedup[key] = time.time()
                ev = {"ts": int(ts), "code": code, "name": name, "industry": ind,
                      "kind": kind, "detail": detail, "px": b.get("close"),
                      "refs": refs, "severity": severity}
                events.append(ev)
                if kind in ("vol_spike", "break", "rs_burst"):
                    fired_codes.setdefault(ind, []).append(code)

            # rule 1: vol spike >= 2.5x vol20
            if vol20 and V[-1] >= 2.5 * vol20:
                fire("vol_spike", f"量 {V[-1]:.0f} ≥ 2.5×vol20({vol20:.0f})，{V[-1] / vol20:.1f}×",
                     ["vol_ratio"], 3 if V[-1] / vol20 >= 4 else 2)
            # rule 2: 5m MA20/MA60 break
            if ma20 is not None:
                prev_diff = C[-2] - (sum(C[-22:-2]) / 20 if len(C) >= 22 else None)
                if prev_diff is not None and prev_diff >= 0 > (C[-1] - ma20):
                    fire("break", f"5m 收破 MA20({ma20:.1f}) 向下", ["ma20"], 2)
                elif prev_diff is not None and prev_diff <= 0 < (C[-1] - ma20):
                    fire("break", f"5m 收上 MA20({ma20:.1f})", ["ma20"], 2)
            if ma60 is not None and len(C) >= 62:
                prev60 = C[-2] - (sum(C[-62:-2]) / 60)
                if prev60 >= 0 > (C[-1] - ma60):
                    fire("break", f"5m 收破 MA60({ma60:.1f}) 向下", ["ma60"], 3)
                elif prev60 <= 0 < (C[-1] - ma60):
                    fire("break", f"5m 收上 MA60({ma60:.1f})", ["ma60"], 2)
            # rule 3: RS burst vs 0050 (15m window = 3 bars)
            if idx50 and len(idx50) >= 4 and len(C) >= 4:
                rs = (C[-1] / C[-4] - 1) * 100 - (idx50[-1] / idx50[-4] - 1) * 100
                if rs >= 0.8:
                    fire("rs_burst", f"15m 相對 0050 跑贏 {rs:.1f}pp", ["rs_vs_0050"], 2)
            # rule 4: frozen bull/bear trigger
            scn = frozen.get(code) or {}
            bull, bear = scn.get("bull"), scn.get("bear")
            if bull and b.get("close") and b["close"] >= bull:
                fire("frozen", f"觸及凍結看多目標 {bull:.1f}", ["frozen_bull"], 4)
            if bear and b.get("close") and b["close"] <= bear:
                fire("frozen", f"觸及凍結看空目標 {bear:.1f}", ["frozen_bear"], 4)

        # rule 5: sector heat — >=3 same industry fired within this scan
        for ind, codes in fired_codes.items():
            if len(codes) >= 3:
                dedup_key = f"sector:{ind}:{int(time.time() / 900)}"  # 15-min dedupe
                if dedup.get(dedup_key, 0) == 0:
                    dedup[dedup_key] = time.time()
                    events.append({"ts": int(time.time()), "code": "", "name": "", "industry": ind,
                                   "kind": "sector", "detail": f"{ind} {len(codes)} 檔 15m 內觸發：{', '.join(codes[:8])}",
                                   "px": None, "refs": ["sector_heat"], "severity": 3, "sector": True,
                                   "codes": codes})

        # append + latest
        if events:
            with (LIVE_DIR / "events.jsonl").open("a", encoding="utf-8") as f:
                for ev in events:
                    f.write(json.dumps(ev, ensure_ascii=False) + "\n")
        existing = []
        try:
            for line in (LIVE_DIR / "events.jsonl").read_text(encoding="utf-8").splitlines():
                if line.strip():
                    existing.append(json.loads(line))
        except Exception:
            pass
        latest = {"generated_at": int(time.time()), "session": {"label": session,
                                                                "range": "09:00–13:30 TPE",
                                                                "in_session": bool(in_session)},
                  "watchlist": wl, "events": existing[-200:]}
        (LIVE_DIR / "latest.json").write_text(json.dumps(latest, ensure_ascii=False), encoding="utf-8")
        _save_dedup(dedup)
        log(f"livescan session={session} watch={len(wl)} events={len(events)}")

        # AI點評: generate a commentator line for the top triggered codes (max 3/scan,
        # highest severity first; deduped by event ts via the comment's event_ts).
        if events and in_session:
            try:
                import comment_feed as cf
                cand = [e for e in events if e.get("code") and not e.get("sector")]
                cand.sort(key=lambda e: e.get("severity", 0), reverse=True)
                seen_codes = set()
                made = 0
                for ev in cand:
                    if made >= 3:
                        break
                    c = ev.get("code")
                    if c in seen_codes:
                        continue
                    seen_codes.add(c)
                    if cf.comment_for_event(c, ev):
                        made += 1
            except Exception:
                pass

        # D4 P0 自動跟踪: high-severity livescan events for FOLLOWED codes append a
        # field-cited comment (source=tracker) — deterministic, no LLM, chart closed
        # is fine. No whole-market 5m: only codes already in the watchlist are scanned.
        followed = set()
        tracked_events = []
        if events:
            try:
                import comment_feed as cf
                followed = cf.followed_codes()
                for ev in events:
                    c = ev.get("code")
                    if c and not ev.get("sector") and ev.get("severity", 0) >= 3 and c in followed:
                        if cf.tracker_comment(c, ev):
                            tracked_events.append(ev)
            except Exception:
                pass

        # high-severity notify marker (launchd script reads this for osascript dedupe)
        high = [e for e in events if e.get("severity", 0) >= 3]
        if high:
            try:
                st = json.loads(NOTIFY_STATE.read_text(encoding="utf-8")) if NOTIFY_STATE.exists() else {}
                st["last_high_ts"] = max([e["ts"] for e in high])
                st["last_high_count"] = len(high)
                st["last_high_kinds"] = sorted({e["kind"] for e in high})
                # D4 P0: which followed codes went high-severity (notify mentions them)
                st["last_high_followed"] = sorted({e["code"] for e in tracked_events})
                NOTIFY_STATE.write_text(json.dumps(st), encoding="utf-8")
            except Exception:
                pass
        return {"ok": True, "session": session, "watch": len(wl), "events": len(events),
                "high": len(high) if high else 0, "tracked": len(tracked_events)}
    finally:
        try:
            LIVE_LOCK.unlink(missing_ok=True)
        except Exception:
            pass


def run_fetch(code: str, tfs: list, need_daily: bool) -> None:
    env = dict(os.environ)
    key = load_key()
    if key:
        env["FUGLE_API_KEY"] = key
    cmds = []
    if tfs:
        cmds.append([sys.executable, "etl/fetch_fugle_candles.py",
                     "--code", code, "--timeframes", ",".join(tfs), "--days", "10", "--sleep", "0.4"])
    if need_daily:
        cmds.append([sys.executable, "etl/fetch_finmind_candles.py",
                     "--code", code, "--days", "400"])
    for c in cmds:
        try:
            r = subprocess.run(c, cwd=str(ROOT), env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                               timeout=180)
            log(f"{code} {' '.join(c[1:])} exit={r.returncode}")
        except Exception as e:  # noqa: BLE001
            log(f"{code} ERR {type(e).__name__}: {e}")
        time.sleep(1)


def _watch_quotes(holdings: list) -> tuple:
    """D7 watch quotes: Finnhub if FINNHUB_API_KEY present, else static seed.
    NEVER returns the key. Unlisted tickers -> source 'static' with seed/null."""
    tickers = [str(h.get("ticker") or "").strip().upper() for h in (holdings or []) if h.get("ticker")]
    if not tickers:
        return [], "none"
    key = ""
    for line in ENV.read_text(encoding="utf-8").splitlines() if ENV.exists() else []:
        line = line.strip()
        if line.startswith("export "):
            line = line[7:]
        if "=" in line and "FINNHUB" in line and "API_KEY" in line:
            key = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not key:
        return [{ "ticker": t, "price": None, "change_pct": None, "market": "closed", "source": "seed" } for t in tickers], "seed"
    try:
        base = "https://finnhub.io"
        quotes, source = [], "finnhub"
        for t in tickers:
            try:
                import urllib.request
                url = f"{base}/quote?symbol={urllib.parse.quote(t)}&token={urllib.parse.quote(key)}"
                with urllib.request.urlopen(url, timeout=8) as r:
                    d = json.loads(r.read().decode("utf-8"))
                quotes.append({
                    "ticker": t,
                    "price": d.get("c"),
                    "change_pct": (d.get("dp")),
                    "high": d.get("h"), "low": d.get("l"), "open": d.get("o"), "prev_close": d.get("pc"),
                    "market": "open" if d.get("t") else "closed",
                    "source": "finnhub",
                })
            except Exception:
                quotes.append({"ticker": t, "price": None, "change_pct": None, "market": "closed", "source": "seed"})
        return quotes, source
    except Exception:
        return [{"ticker": t, "price": None, "change_pct": None, "market": "closed", "source": "seed"} for t in tickers], "seed"


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, obj: dict) -> None:
        b = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_OPTIONS(self) -> None:  # CORS preflight from the 8777 page
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.end_headers()

    def _p2_state(self, code: str) -> dict:
        running = False
        if P2_LOCK.exists():
            try:
                cur = json.loads(P2_LOCK.read_text())
                running = cur.get("code") == code and (time.time() - cur.get("ts", 0)) < 300
            except Exception:
                running = False
        return {"running": running}

    def _append_timeline(self, code: str, action: str, proposal: str, target, backup, as_of) -> None:
        """WAVE 4 P3: append an adopt/reject event to data/research/history/timeline.jsonl."""
        hdir = ROOT / "data" / "research" / "history"
        hdir.mkdir(parents=True, exist_ok=True)
        tf = hdir / "timeline.jsonl"
        row = {"code": code, "action": action, "proposal": proposal, "target": target,
               "backup": backup, "as_of": as_of,
               "ts": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")}
        try:
            with tf.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        except Exception as e:
            log(f"timeline append failed: {type(e).__name__}: {e}")

    def do_GET(self) -> None:
        q = urllib.parse.urlparse(self.path).query
        p = urllib.parse.parse_qs(q)
        path = urllib.parse.urlparse(self.path).path
        code = (p.get("code", [""]) or [""])[0].strip().upper()
        if path == "/livescan":
            out = live_scan(force_refresh=True)
            self._send(200, out)
            return
        if path == "/p2":
            code = (p.get("code", [""]) or [""])[0].strip().upper()
            self._send(200, {"code": code, **self._p2_state(code)})
            return
        if path == "/comments":
            code = (p.get("code", [""]) or [""])[0].strip().upper()
            date = (p.get("date", [""]) or [""])[0].strip()
            if not code:
                self._send(400, {"error": "code required"})
                return
            import comment_feed as cf
            rows = cf.comments_for_date(code, date) if date else cf.load_comments(code)
            self._send(200, {"code": code, "dates": cf.comment_dates(code), "rows": rows,
                             "feed": cf.build_feed(rows)})
            return
        if path == "/reassess":
            code = (p.get("code", [""]) or [""])[0].strip().upper()
            pf = Path(f"/tmp/reassess_{code}.json")
            if not code or not pf.exists():
                self._send(200, {"code": code, "status": None})
                return
            try:
                st = json.loads(pf.read_text(encoding="utf-8"))
            except Exception:
                st = None
            # stale > 15 min = treat as not running
            if st and st.get("running") and time.time() - st.get("updated_at", 0) > 900:
                st = None
            self._send(200, {"code": code, "status": st})
            return
        if path == "/history":
            code = (p.get("code", [""]) or [""])[0].strip().upper()
            if not code:
                self._send(400, {"error": "code required"})
                return
            self._send(200, {"code": code, "rows": history_rows(code)})
            return
        if path == "/recap":
            self._send(200, {"rows": recap_rows()})
            return
        if path == "/follow":
            code = (p.get("code", [""]) or [""])[0].strip().upper()
            if not code:
                self._send(400, {"error": "code required"})
                return
            self._send(200, {"code": code, "state": follow_state(code)})
            return
        if path == "/research-deep":
            # WAVE 3 P2: poll deep-research job status (phase file written by etl/research_deep.py)
            pf = Path(f"/tmp/deepresearch_{code}.json")
            if not code or not pf.exists():
                self._send(200, {"code": code, "status": None})
                return
            try:
                st = json.loads(pf.read_text(encoding="utf-8"))
            except Exception:
                st = None
            if st and st.get("running") and time.time() - st.get("updated_at", 0) > 900:
                st = {**st, "running": False, "phase": "error", "activity": "timeout (15m)"}
            self._send(200, {"code": code, "status": st})
            return
        if path == "/research-refresh":
            # WAVE 4 P3: poll refresh job status (phase file written by etl/research_refresh.py)
            pf = Path(f"/tmp/researchrefresh_{code}.json")
            if not code or not pf.exists():
                self._send(200, {"code": code, "status": None})
                return
            try:
                st = json.loads(pf.read_text(encoding="utf-8"))
            except Exception:
                st = None
            if st and st.get("running") and time.time() - st.get("updated_at", 0) > 900:
                st = {**st, "running": False, "phase": "error", "activity": "timeout (15m)"}
            self._send(200, {"code": code, "status": st})
            return
        if path == "/research-proposals":
            # WAVE 4 P3: list a code's proposals + optionally read one (file= in query).
            d = ROOT / "data" / "research" / "proposals"
            out = []
            if d.is_dir():
                for f in sorted(d.glob(f"{code}-*.md"), reverse=True):
                    sc = f.with_name(f.name + ".diff.json")
                    meta = _read_json_safe(sc) or {}
                    out.append({"id": f.name, "file": f.name, "created_at": meta.get("created_at"),
                                "status": meta.get("status", "open"),
                                "diff": meta.get("diff"),
                                "sec_added": len(meta.get("sections", {}).get("added", [])),
                                "sec_changed": len(meta.get("sections", {}).get("changed", [])),
                                "sec_removed": len(meta.get("sections", {}).get("removed", []))})
            want = (p.get("file", [""]) or [""])[0]
            extra = None
            if want:
                pf = d / want
                scf = pf.with_name(want + ".diff.json")
                extra = {"file": want,
                         "text": pf.read_text(encoding="utf-8") if pf.exists() else None,
                         "diff": _read_json_safe(scf)}
            self._send(200, {"code": code, "proposals": out, "detail": extra})
            return
        if path == "/research-timeline":
            # WAVE 4 P3: adopt/reject history for a code (data/research/history/timeline.jsonl)
            tf = ROOT / "data" / "research" / "history" / "timeline.jsonl"
            rows = []
            if tf.exists():
                for line in tf.read_text(encoding="utf-8").splitlines():
                    if not line.strip():
                        continue
                    try:
                        r = json.loads(line)
                    except Exception:
                        continue
                    if str(r.get("code", "")).zfill(4) == code:
                        rows.append(r)
            self._send(200, {"code": code, "rows": rows})
            return
        if path == "/memory":
            code = (p.get("code", [""]) or [""])[0].strip().upper()
            u = _read_json_safe(_mem_user_path())
            s = _read_json_safe(_mem_symbol_path(code)) if code else None
            self._send(200, {"user": u, "symbol": s, "code": code,
                             "present": memory_context(code)["present"]})
            return
        if path == "/research-read":
            # WAVE 3 P2: read a research file's text. ?code=2454&deep=1 -> latest {code}-deep-*.md ; else {code}.md
            deep = bool(p.get("deep", [""])[0])
            if not code:
                self._send(400, {"error": "code required"})
                return
            d = ROOT / "data" / "research"
            target = None
            if deep and d.is_dir():
                cands = sorted(d.glob(f"{code}-deep-*.md"), reverse=True)
                if cands:
                    target = cands[0]
            if target is None:
                target = d / f"{code}.md"
            if not target.exists():
                self._send(200, {"code": code, "deep": deep, "text": None, "name": None})
                return
            self._send(200, {"code": code, "deep": deep, "name": target.name,
                             "text": target.read_text(encoding="utf-8"),
                             "mtime": int(target.stat().st_mtime)})
            return
        if path == "/research":
            out = []
            d = ROOT / "data" / "research"
            if d.is_dir():
                for f in sorted(d.glob("*.md"), reverse=True):
                    stem = f.stem
                    deep = stem.rsplit("-deep-", 1)
                    out.append({"name": f.name, "stem": stem, "deep": bool(deep) and len(deep) == 2,
                                "code": (deep[0] if deep and len(deep) == 2 else stem),
                                "size": f.stat().st_size,
                                "mtime": int(f.stat().st_mtime)})
            self._send(200, {"docs": out})
            return
        if path == "/news":
            code = (p.get("code", [""]) or [""])[0].strip().upper()
            if not code:
                self._send(400, {"error": "code required"})
                return
            out = run_news(code, refresh=bool(p.get("refresh", [""])[0]))
            self._send(200, out)
            return
        if path == "/watch/nvidia":
            base = ROOT / "data" / "watch" / "nvidia"
            def _load(name):
                f = base / name
                try:
                    return json.loads(f.read_text(encoding="utf-8"))
                except Exception:
                    return None
            holdings = _load("holdings.json") or {}
            timeline = _load("timeline.json") or {}
            cache_f = base / "quotes_cache.json"
            cache = None
            try:
                cache = json.loads(cache_f.read_text(encoding="utf-8"))
            except Exception:
                cache = None
            quotes, qsource = _watch_quotes(holdings.get("holdings") or [])
            self._send(200, {
                "holdings": holdings,
                "timeline": timeline,
                "quotes": quotes,
                "quotes_source": qsource,
                "quotes_cached_at": (cache or {}).get("updated"),
            })
            return
        if path == "/watch/quotes":
            tickers_raw = (p.get("tickers", [""]) or [""])[0]
            tickers = [t.strip().upper() for t in tickers_raw.split(",") if t.strip()]
            if not tickers:
                self._send(400, {"error": "tickers required (comma-separated)"})
                return
            quotes, qsource = _watch_quotes([{"ticker": t} for t in tickers])
            self._send(200, {"quotes": quotes, "quotes_source": qsource})
            return
        code = (p.get("code", [""])[0] or "").strip().upper()
        if not code:
            self._send(400, {"error": "code required"})
            return
        self._send(200, {
            "code": code,
            "daily": daily_state(code),
            "tfs": {tf: tf_state(code, tf) for tf in ("5", "15", "60")},
        })

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0") or 0)
        body = self.rfile.read(length) if length else b""
        try:
            req = json.loads(body.decode("utf-8") or "{}")
        except Exception:
            req = {}
        path = urllib.parse.urlparse(self.path).path
        p = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        code = str(req.get("code", "") or (p.get("code", [""]) or [""])[0]).strip().upper()

        if path == "/p2":
            if not code or len(code) != 4 or not code.isalnum():
                self._send(400, {"error": "code required"})
                return
            if self._p2_state(code)["running"]:
                self._send(202, {"started": False, "running": True, "code": code})
                return
            P2_LOCK.write_text(json.dumps({"code": code, "ts": time.time()}))
            log(f"p2 {code}")
            # lock TTL (300s in _p2_state) matches the subprocess timeout below
            subprocess.Popen(
                [sys.executable, "-c",
                 f"import subprocess,sys; subprocess.run([sys.executable,'etl/cockpit_p2.py','{code}'],cwd=r'{ROOT}',stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=300)"],
                cwd=str(ROOT), start_new_session=True,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._send(202, {"started": True, "code": code})
            return

        if path == "/reassess":
            if not code or len(code) != 4 or not code.isalnum():
                self._send(400, {"error": "code required"})
                return
            origin = str(req.get("origin") or "manual")
            if origin not in ("manual", "escalation"):
                origin = "manual"
            pf = Path(f"/tmp/reassess_{code}.json")
            if pf.exists():
                try:
                    st = json.loads(pf.read_text(encoding="utf-8"))
                    if st.get("running") and time.time() - st.get("updated_at", 0) < 900:
                        self._send(202, {"started": False, "reason": "already-running", "code": code})
                        return
                except Exception:
                    pass
            log(f"reassess {code} origin={origin}")
            subprocess.Popen(
                [sys.executable, "etl/run_reassess.py", code, origin],
                cwd=str(ROOT), start_new_session=True,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._send(202, {"started": True, "code": code, "origin": origin})
            return

        if path == "/explain":
            if not code or len(code) != 4 or not code.isalnum():
                self._send(400, {"error": "code required"})
                return
            try:
                import comment_feed as cf
                rows = []
                for line in (ROOT / "data" / "cockpit" / "cockpit.jsonl").read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        r = json.loads(line)
                        if str(r.get("code", "")).zfill(4) == code:
                            rows.append(r)
                if not rows:
                    self._send(400, {"ok": False, "error": "尚無凍結點評（先跑 p2）"})
                    return
                out = cf.explainer_comment(code, rows[-1])
                if not out.get("text"):
                    self._send(200, {"ok": False, "error": "LLM 未回傳解釋"})
                    return
                row = {"ts": int(time.time()), "text": out["text"], "level": "info",
                       "source": "explainer", "stance": out.get("stance"),
                       "stance_note": out.get("stance_note"), "as_of": rows[-1].get("as_of")}
                cf.append_comment(code, row)
                self._send(200, {"ok": True, "comment": row})
            except Exception as e:
                self._send(200, {"ok": False, "error": f"{type(e).__name__}: {e}"})
            return

        if path == "/research-deep":
            # WAVE 3 P2: start deep-research job (six-section md). Subprocess, poll /research-deep?code=
            if not code or len(code) != 4 or not code.isalnum():
                self._send(400, {"error": "code required"})
                return
            pf = Path(f"/tmp/deepresearch_{code}.json")
            if pf.exists():
                try:
                    st = json.loads(pf.read_text(encoding="utf-8"))
                    if st.get("running") and time.time() - st.get("updated_at", 0) < 900:
                        self._send(202, {"started": False, "reason": "already-running", "code": code})
                        return
                except Exception:
                    pass
            log(f"research-deep {code}")
            subprocess.Popen(
                [sys.executable, "etl/research_deep.py", code],
                cwd=str(ROOT), start_new_session=True,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._send(202, {"started": True, "code": code})
            return

        if path == "/research-refresh":
            # WAVE 4 P3: start a research refresh job (re-write + proposal + diff). Subprocess, poll /research-refresh?code=
            if not code or len(code) != 4 or not code.isalnum():
                self._send(400, {"error": "code required"})
                return
            target = str(req.get("path") or "").strip().lstrip("/")
            if target and (not target.endswith(".md") or "/" in target):
                self._send(400, {"error": "path must be a bare *.md filename"})
                return
            target = target or f"{code}.md"
            pf = Path(f"/tmp/researchrefresh_{code}.json")
            if pf.exists():
                try:
                    st = json.loads(pf.read_text(encoding="utf-8"))
                    if st.get("running") and time.time() - st.get("updated_at", 0) < 900:
                        self._send(202, {"started": False, "reason": "already-running", "code": code})
                        return
                except Exception:
                    pass
            if not (ROOT / "data" / "research" / target).exists():
                self._send(400, {"ok": False, "error": f"no research file to refresh: {target}"})
                return
            args = [sys.executable, "etl/research_refresh.py", code, target]
            log(f"research-refresh {code} {target}")
            subprocess.Popen(args, cwd=str(ROOT), start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self._send(202, {"started": True, "code": code, "target": target})
            return

        if path == "/research-adopt":
            # WAVE 4 P3: adopt/reject a refresh proposal.
            # adopt: backup current md -> history/, overwrite md, mark sidecar adopted, append timeline.
            # reject: mark sidecar rejected; md unchanged.
            action = str(req.get("action") or "").strip().lower()
            proposal = str(req.get("proposal") or "").strip()
            if action not in ("adopt", "reject"):
                self._send(400, {"ok": False, "error": "action must be adopt|reject"})
                return
            if not code or len(code) != 4 or not code.isalnum():
                self._send(400, {"ok": False, "error": "code required"})
                return
            if not proposal or "/" in proposal or not proposal.endswith(".md"):
                self._send(400, {"ok": False, "error": "proposal must be a bare <code>-<ts>.md filename"})
                return
            if not proposal.startswith(code + "-"):
                self._send(400, {"ok": False, "error": "proposal filename must start with the code"})
                return
            pdir = ROOT / "data" / "research" / "proposals"
            pfile = pdir / proposal
            sidecar = pfile.with_name(proposal + ".diff.json")
            meta = _read_json_safe(sidecar)
            if not pfile.exists() or not meta:
                self._send(404, {"ok": False, "error": "proposal not found"})
                return
            cur = meta.get("status", "open")
            if cur in ("adopted", "rejected"):
                self._send(409, {"ok": False, "error": f"proposal already {cur}"})
                return
            now_iso = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
            if action == "reject":
                meta["status"] = "rejected"
                meta["rejected_at"] = now_iso
                sidecar.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
                self._append_timeline(code, "reject", proposal, meta.get("target"), None, meta.get("as_of"))
                self._send(200, {"ok": True, "code": code, "action": "reject", "proposal": proposal,
                                 "status": "rejected"})
                return
            # adopt
            target = meta.get("target") or f"{code}.md"
            tpath = ROOT / "data" / "research" / target
            if not tpath.exists():
                self._send(409, {"ok": False, "error": f"target md missing: {target}"})
                return
            hdir = ROOT / "data" / "research" / "history"
            hdir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now(timezone(timedelta(hours=8))).strftime("%Y%m%d-%H%M%S")
            backup = hdir / f"{code}-backup-{ts}.md"
            backup.write_text(tpath.read_text(encoding="utf-8"), encoding="utf-8")
            new_text = pfile.read_text(encoding="utf-8")
            try:
                tpath.write_text(new_text, encoding="utf-8")
            except Exception as e:
                self._send(500, {"ok": False, "error": f"md 覆寫失敗 {type(e).__name__}: {e}"})
                return
            # mark sidecar immediately after md write so a crash can't leave the proposal "open"
            meta["status"] = "adopted"
            meta["adopted_at"] = now_iso
            try:
                sidecar.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
                self._append_timeline(code, "adopt", proposal, target, backup.name, meta.get("as_of"))
            except Exception as e:
                log(f"adopt sidecar/timeline partial: {type(e).__name__}: {e}")
            log(f"research-adopt {code} {proposal} -> {target} (backup {backup.name})")
            self._send(200, {"ok": True, "code": code, "action": "adopt", "proposal": proposal,
                             "target": target, "backup": backup.name, "status": "adopted"})
            return

        if path == "/memory":
            # WAVE 3 P1: edit / clear user memory and per-symbol memory.
            # Frontend sends the full object it wants persisted (or {} to clear a field).
            action = str(req.get("action") or "save").strip()
            target = str(req.get("scope") or "user").strip().lower()
            if target not in ("user", "symbol"):
                self._send(400, {"ok": False, "error": "scope must be user|symbol"})
                return
            payload = req.get("data") or {}
            if target == "symbol":
                if not code or len(code) != 4 or not code.isalnum():
                    self._send(400, {"ok": False, "error": "code required for symbol memory"})
                    return
                pth = _mem_symbol_path(code)
            else:
                pth = _mem_user_path()
            if action == "clear":
                # clear = delete file (symbol) or reset to {} (user keeps schema)
                if target == "symbol":
                    pth.unlink(missing_ok=True)
                    self._send(200, {"ok": True, "scope": "symbol", "code": code,
                                     "cleared": True, "present": False})
                else:
                    pth.parent.mkdir(parents=True, exist_ok=True)
                    pth.write_text(json.dumps({}, ensure_ascii=False), encoding="utf-8")
                    self._send(200, {"ok": True, "scope": "user", "cleared": True, "present": False})
                return
            # save
            pth.parent.mkdir(parents=True, exist_ok=True)
            existing = _read_json_safe(pth) or {}
            merged = {**existing, **payload}
            # strip null/empty values so "clear a field" (send null) works
            for k in list(merged.keys()):
                if merged[k] is None or merged[k] == "" or merged[k] == []:
                    merged.pop(k, None)
            pth.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
            log(f"memory save scope={target} code={code} keys={list(merged.keys())}")
            self._send(200, {"ok": True, "scope": target, "code": code,
                             "present": True, "saved": merged})
            return

        if path == "/research-save":
            if not code or len(code) != 4 or not code.isalnum():
                self._send(400, {"error": "code required"})
                return
            md = str(req.get("markdown") or "").strip()
            if not md:
                self._send(400, {"error": "markdown required"})
                return
            d = ROOT / "data" / "research"
            d.mkdir(parents=True, exist_ok=True)
            (d / f"{code}.md").write_text(md, encoding="utf-8")
            log(f"research save {code} ({len(md)}B)")
            self._send(200, {"ok": True, "code": code, "size": len(md)})
            return

        if path == "/follow":
            if not code or len(code) != 4 or not code.isalnum():
                self._send(400, {"error": "code required"})
                return
            if req.get("cancel"):
                follow_path(code).unlink(missing_ok=True)
                self._send(200, {"ok": True, "following": False, "code": code})
                return
            try:
                entry = float(req["entry"]); target = float(req["target"]); stop = float(req["stop"])
            except Exception:
                self._send(400, {"error": "entry/target/stop required"})
                return
            st = {"code": code, "entry": entry, "target": target, "stop": stop,
                  "direction": "long" if target > entry else "short",
                  "ts": time.time(), "triggered": False, "trigger_at": None}
            FOLLOW_DIR.mkdir(parents=True, exist_ok=True)
            follow_path(code).write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
            log(f"follow {code} e={entry} t={target} s={stop}")
            self._send(200, {"ok": True, "following": True, "code": code, "state": st})
            return

        if path == "/research-draft":
            if not code or len(code) != 4 or not code.isalnum():
                self._send(400, {"error": "code required"})
                return
            try:
                import comment_feed as cf
                # (datetime/timedelta/timezone already imported at module top — do NOT re-import
                #  here: a local `datetime` would shadow the module one for the whole do_POST scope
                #  and break every other POST handler's datetime.now() with UnboundLocalError.)
                tpe = timezone(timedelta(hours=8))
                doc = (ROOT / "data" / "candles" / f"{code}.json")
                d = json.loads(doc.read_text(encoding="utf-8")) if doc.exists() else {}
                daily = (d.get("daily") or [])[-30:]
                fx = cf._fundrow(code)
                frozen = []
                for line in (ROOT / "data" / "cockpit" / "cockpit.jsonl").read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        r = json.loads(line)
                        if str(r.get("code", "")).zfill(4) == code:
                            frozen.append({"as_of": r.get("as_of"), "scenarios": r.get("scenarios"),
                                           "weights_pct": r.get("weights_pct")})
                prompt = (
                    f"你是台股研究員。為代碼 {code} 起草一份研究庫文件（markdown，400-700字），章節："
                    "## 現況（價格/量能/外資）、## 技術結構（MA20/50、MACD、RSI 讀法）、"
                    "## 情景（多/基準/空 三檔位與觸發條件）、## 風險。"
                    "每句結論引用給定欄位；資料不足直說。直接回 markdown 全文，不要 JSON 包裹。\n"
                    f"代碼 {code} 日期 {datetime.now(tpe).strftime('%Y-%m-%d')}\n"
                    f"近30日K: {json.dumps([{k: b.get(k) for k in ('time','open','high','low','close','volume')} for b in daily], ensure_ascii=False)}\n"
                    f"FundFlo: {json.dumps(fx, ensure_ascii=False)}\n"
                    f"近期凍結點評: {json.dumps(frozen[-3:], ensure_ascii=False)}"
                )
                payload = {"model": os.environ.get("COCKPIT_LLM_MODEL", "qwen3.8-flash-next"), "messages": [{"role": "user", "content": prompt}],
                           "max_tokens": 1600, "temperature": 0.3,
                           "chat_template_kwargs": {"enable_thinking": False}}
                r2 = urllib.request.Request(LLM_URL + "/chat/completions",
                                            data=json.dumps(payload).encode(),
                                            headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(r2, timeout=240) as resp:
                    out = json.loads(resp.read().decode())
                msg = (out.get("choices") or [{}])[0].get("message") or {}
                text = (msg.get("content") or msg.get("reasoning") or "").strip()
                if not text:
                    self._send(200, {"ok": False, "error": "LLM 未回傳內容"})
                    return
                self._send(200, {"ok": True, "markdown": text, "code": code})
            except Exception as e:
                self._send(200, {"ok": False, "error": f"{type(e).__name__}: {e}"})
            return

        if path == "/ask":
            q = str(req.get("question", "")).strip()
            ctx = req.get("context") or {}
            if not code or not q:
                self._send(400, {"error": "code + question required"})
                return
            def clip(v, n=40):
                return str(v)[:n]
            bars = [b for b in (ctx.get("bars") or []) if isinstance(b, dict)][-30:]
            bars_s = json.dumps([{k: b.get(k) for k in ("time", "open", "high", "low", "close", "volume") if k in b} for b in bars], ensure_ascii=False)
            ov = {k: clip(v, 24) for k, v in (ctx.get("overlays") or {}).items()}
            fl = {k: clip(v, 24) for k, v in (ctx.get("fundflo") or {}).items()}
            doc_excerpt = str(ctx.get("doc_excerpt") or ctx.get("doc") or "")[:3000]
            mem_block = memory_render(code)
            prompt = ("你是台股駕駛艙助手。用繁體中文簡短回答（<120字）。每句結論必須引用給定欄位"
                      "（close/MA20/HIST/RSI/vol_ratio/foreign_net_yi 等）；資料不足就直說；不給投資建議。\n"
                      f"代碼 {code} 週期 {clip(ctx.get('tf'), 8)}\n"
                      f"疊加欄位: {json.dumps(ov, ensure_ascii=False)}\n"
                      f"法人 FundFlo: {json.dumps(fl, ensure_ascii=False)}\n"
                      + (f"研究檔摘錄:\n{doc_excerpt}\n" if doc_excerpt else "")
                      + (f"{mem_block}\n" if mem_block else "")
                      + f"近{len(bars)}根K: {bars_s}\n"
                      f"問: {q[:200]}")
            try:
                payload = {"model": os.environ.get("COCKPIT_LLM_MODEL", "qwen3.8-flash-next"),
                           "messages": [{"role": "user", "content": prompt}],
                           "max_tokens": 512, "temperature": 0.2}
                rr = urllib.request.Request(LLM_URL + "/chat/completions",
                                            data=json.dumps(payload).encode(),
                                            headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(rr, timeout=120) as resp:
                    out = json.loads(resp.read().decode())
                msg = ((out.get("choices") or [{}])[0].get("message") or {})
                ans = (msg.get("content") or msg.get("reasoning") or msg.get("reasoning_content") or "").strip()
                self._send(200, {"ok": bool(ans), "answer": ans[-1200:], "llm": "local-vllm"})
            except Exception as e:
                import traceback
                try:
                    with open("/tmp/candle_helper.log", "a", encoding="utf-8") as f2:
                        f2.write("ASK TRACEBACK:\n" + traceback.format_exc() + "\n")
                except Exception:
                    pass
                self._send(200, {"ok": False, "error": f"LLM 離線: {type(e).__name__}: {e}"})
            return

        if not code or len(code) != 4 or not code.isalnum():
            self._send(400, {"error": "code must be a 4-digit TWSE/TPEx id"})
            return
        tfs = [str(t).strip() for t in (req.get("tfs") or ["5", "15", "60"])]
        need_daily = bool(req.get("daily")) or not daily_state(code)["present"]
        # dedupe: ignore if a fetch is already running for this code
        lock_key = f"code={code}"
        if LOCK.exists():
            try:
                cur = json.loads(LOCK.read_text())
                if cur.get("code") == code and (time.time() - cur.get("ts", 0)) < 240:
                    self._send(202, {"started": False, "reason": "already-running", "code": code})
                    return
            except Exception:
                pass
        LOCK.write_text(json.dumps({"code": code, "ts": time.time()}))
        log(f"fetch {code} tfs={tfs} daily={need_daily}")
        # spawn detached so the POST returns fast
        subprocess.Popen(
            [sys.executable, "-c",
             f"import sys; sys.path.insert(0,'{ROOT}/etl'); "
             f"import candle_server as cs; cs.run_fetch({code!r}, {tfs!r}, {bool(need_daily)!r})"],
            cwd=str(ROOT), start_new_session=True,
        )
        self._send(202, {"started": True, "code": code, "tfs": tfs, "daily_missing": need_daily})

    def log_message(self, *a) -> None:  # silence
        pass


def main() -> None:
    os.makedirs(OUT, exist_ok=True)
    ThreadingHTTPServer.allow_reuse_address = True
    HOST = os.environ.get("CANDLE_HOST", "0.0.0.0")
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    log(f"helper listening on 127.0.0.1:{PORT}")
    srv.serve_forever()


if __name__ == "__main__":
    main()
