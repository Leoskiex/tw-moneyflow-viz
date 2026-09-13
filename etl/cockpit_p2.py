#!/usr/bin/env python3
"""P2 句句有据 — local LLM comment + frozen predictions + hit-rate scoring.

Feeds: data/candles/<code>.json, data/candles/0050.json, data/candles/<code>_news.json,
       data/regime_latest.json, data/fundflo/latest.json (read-only).
LLM: local vLLM on the head box (OpenAI-compatible /v1), URL from env COCKPIT_LLM_URL
     (fallback http://192.168.31.151:8888/v1). No keys in html.
Outputs:
  data/cockpit/cockpit.jsonl        append-only frozen rows (one json per line)
  data/research/<code>.md           latest comment + evidence table
  /tmp/p2_score.json                scoring report (n, hit%)

Usage: python3 etl/cockpit_p2.py [2330]
"""
from __future__ import annotations

import json
import os
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
TZ8 = timezone(timedelta(hours=8))


def sma(a, n):
    out = []
    s = 0.0
    for i, v in enumerate(a):
        s += v
        if i >= n:
            s -= a[i - n]
        out.append(s / n if i >= n - 1 else None)
    return out


def load_json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return None


def compute(code):
    doc = load_json(DATA / "candles" / f"{code}.json")
    if not doc or not doc.get("daily"):
        return None
    bars = doc["daily"]
    C = [b["close"] for b in bars]
    V = [b.get("volume") or 0 for b in bars]
    m20 = sma(C, 20)[-1]
    m50 = sma(C, 50)[-1]
    n = len(C)
    # histogram proxy: close minus ema-like via 9-window of dif
    m12 = sma(C, 12)
    m26 = sma(C, 26)
    dif = [(m12[i] - m26[i]) if (m12[i] is not None and m26[i] is not None) else None for i in range(n)]
    dea = sma([d for d in dif if d is not None], 9)
    last_dif = dif[-1]
    last_dea = dea[-1] if dea[-1] is not None else last_dif
    hist = (last_dif - last_dea) if last_dif is not None else None
    # rsi14 (wilder)
    ag = al = 0.0
    rs = None
    for i in range(1, n):
        g = max(C[i] - C[i - 1], 0)
        l = max(C[i - 1] - C[i], 0)
        if i <= 14:
            ag += g
            al += l
            if i == 14:
                ag, al = ag / 14, al / 14
                rs = 50.0 if al == 0 else 100 - 100 / (1 + ag / al)
        else:
            ag, al = (ag * 13 + g) / 14, (al * 13 + l) / 14
            rs = 50.0 if al == 0 else 100 - 100 / (1 + ag / al)
    ff = load_json(DATA / "fundflo" / "latest.json") or {}
    ffrow = None
    for s in (ff.get("stocks") or []):
        if s.get("code") == code:
            ffrow = s
            break
    reg = load_json(DATA / "regime_latest.json") or {}
    news = load_json(DATA / "candles" / f"{code}_news.json") or {}
    return {
        "code": code, "as_of": bars[-1]["time"], "close": C[-1],
        "ma20": m20, "ma50": m50, "hist": hist, "rsi14": rs,
        "vol_ratio": (V[-1] / sma(V, 20)[-1]) if sma(V, 20)[-1] else None,
        "foreign_flow_yi": (ffrow or {}).get("foreign_flow_yi"),
        "combined_5d_yi": (ffrow or {}).get("rolling_combined_5d_yi"),
        "regime": reg.get("primary_label") or reg.get("primary"),
        "regime_conf": reg.get("confidence"),
        "news_top": (news.get("items") or [{}])[0].get("title"),
        "n_bars": n,
    }


def llm_comment(facts):
    url = (os.environ.get("COCKPIT_LLM_URL") or "http://192.168.31.151:8888/v1").rstrip("/")
    lines = [f"{k}={v}" for k, v in facts.items() if v is not None]
    body = {
        "model": os.environ.get("COCKPIT_LLM_MODEL", "qwen3.8-flash-next"),
        "temperature": 0,
        "messages": [{"role": "user", "content":
            "用繁體中文，每句以「欄位=值」引用下列本機欄位，不造價，不寫無來源數字，四句內總結："
            + "; ".join(lines)}],
    }
    req = urllib.request.Request(url + "/chat/completions",
                                 data=json.dumps(body).encode(), method="POST",
                                 headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=90) as r:
            j = json.load(r)
        return j["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"(llm fail {type(e).__name__}: {e})"


def scenarios(f):
    p = f["close"]
    return {"bull": round(p * 1.08, 2), "base": round(p, 2), "bear": round(p * 0.93, 2)}


def score(code):
    """Backfill score: rebuild frozen targets at each of last N bars, test vs +5d close."""
    doc = load_json(DATA / "candles" / f"{code}.json") or {}
    bars = doc.get("daily") or []
    C = [b["close"] for b in bars]
    hits = 0
    rows = []
    for i in range(max(0, len(C) - 21), len(C) - 5):
        p = C[i]
        tgt = {"bull": p * 1.08, "base": p, "bear": p * 0.93}
        actual = C[i + 5]
        tol = 0.015
        best = min(tgt, key=lambda k: abs(tgt[k] - actual))
        ok = abs(tgt[best] - actual) / p <= tol
        hits += ok
        rows.append({"as_of": bars[i]["time"], "pivot": p, "actual_5d": actual,
                    "best": best, "hit": bool(ok)})
    n = len(rows)
    return {"code": code, "n": n, "hits": hits, "hit_pct": round(100 * hits / n, 1) if n else None,
            "rows_tail": rows[-3:]}


def main():
    code = "2330"
    f = compute(code)
    if not f:
        print("no cache for", code)
        return 1
    cmt = llm_comment(f)
    sc = scenarios(f)
    # scenario weights: same rule engine as sepa.html rail
    bull, base, bear = 34, 33, 33
    trg = []
    if f["ma20"]:
        if f["close"] > f["ma20"]:
            bull += 10
            trg.append(f"close {f['close']} > ma20 {round(f['ma20'], 1)}")
        else:
            bear += 10
            trg.append(f"close {f['close']} < ma20 {round(f['ma20'], 1)}")
    if f["hist"] is not None:
        if f["hist"] >= 0:
            bull += 8
            trg.append("hist>=0")
        else:
            bear += 8
            trg.append("hist<0")
    if f["rsi14"] is not None:
        if f["rsi14"] >= 55:
            bull += 6
        elif f["rsi14"] <= 45:
            bear += 6
        else:
            base += 6
        trg.append(f"rsi14={round(f['rsi14'], 1)}")
    tot = bull + base + bear
    w = {k: round(v * 100 / tot) for k, v in [("bull", bull), ("base", base), ("bear", bear)]}
    row = {"as_of": f["as_of"], "code": code, "pivot": f["close"], "scenarios": sc,
           "weights_pct": w, "triggers": trg, "fields": {k: v for k, v in f.items() if v is not None},
           "comment": cmt, "model": os.environ.get("COCKPIT_LLM_MODEL", "qwen3.8-flash-next"),
           "created_at": datetime.now(TZ8).isoformat(timespec="seconds")}
    (DATA / "cockpit").mkdir(parents=True, exist_ok=True)
    (DATA / "research").mkdir(parents=True, exist_ok=True)
    with (DATA / "cockpit" / "cockpit.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    md = [f"# {code} 研究檔（as_of {f['as_of']}）", "", "## 點評（句句引用本機欄位）", "", cmt, "",
          "## 引用欄位", "", "| 欄位 | 值 |", "|---|---|"]
    md += [f"| {k} | {v} |" for k, v in f.items()]
    md += ["", "## 凍結情景（jsonl 末行）", "",
           f"- bull {sc['bull']} ({w['bull']}%)", f"- base {sc['base']} ({w['base']}%)",
           f"- bear {sc['bear']} ({w['bear']}%)", f"- triggers: {', '.join(trg) or '—'}", ""]
    (DATA / "research" / f"{code}.md").write_text("\n".join(md), encoding="utf-8")
    rep = score(code)
    (Path("/tmp") / "p2_score.json").write_text(json.dumps(rep, ensure_ascii=False), encoding="utf-8")
    print("COMMENT:", cmt[:400])
    print("WEIGHTS:", w, "SCN:", sc, "TRIG:", trg)
    print("SCORE:", {k: rep[k] for k in ("n", "hits", "hit_pct")})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
