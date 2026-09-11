#!/usr/bin/env python3
"""Fetch TW stock candles from FinMind into data/candles/ (NOT FundFlo / refresh_daily).

Usage:
  python3 etl/fetch_finmind_candles.py --code 2330
  python3 etl/fetch_finmind_candles.py --code 2330 --with-intraday

Reads FINMIND_TOKEN from env, else /home/box/sand-data/box-secrets.json card.FINMIND_TOKEN.
Never prints the token.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "candles"
API = "https://api.finmindtrade.com/api/v4/data"
TZ8 = timezone(timedelta(hours=8))
SECRETS = Path("/home/box/sand-data/box-secrets.json")


def _looks_like_token(s: str) -> bool:
    ascii_t = "".join(ch for ch in s if ord(ch) < 128).strip()
    if len(ascii_t) < 20 or " " in ascii_t or "\n" in ascii_t:
        return False
    # plan-paste leftovers often mostly spaces/CJK; real tokens are dense alnum/._-
    alnum = sum(c.isalnum() for c in ascii_t)
    return alnum / max(len(ascii_t), 1) >= 0.8


def load_token() -> Optional[str]:
    """Optional. Prefer a valid-looking token from env or box-secrets.
    Free-tier TaiwanStockPrice works anonymously; token raises rate limit.
    Rejects plan-description pastes (spaces / low alnum ratio).
    """
    candidates: list[str] = []
    env = (os.environ.get("FINMIND_TOKEN") or "").strip()
    if env:
        candidates.append(env)
    if SECRETS.exists():
        doc = json.loads(SECRETS.read_text())
        card = doc.get("card") or {}
        sec = (card.get("FINMIND_TOKEN") or "").strip()
        if sec:
            candidates.append(sec)
    for t in candidates:
        if _looks_like_token(t):
            return "".join(ch for ch in t if ord(ch) < 128).strip()
    return None


def api_get(token: Optional[str], params: dict[str, str], timeout: int = 90) -> dict[str, Any]:
    q = urllib.parse.urlencode(params)
    headers = {
        "Accept": "application/json",
        "User-Agent": "tw-moneyflow-candles/0.1",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(
        f"{API}?{q}",
        headers=headers,
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    return json.loads(body)


def fetch_daily(token: str, code: str, start: str, end: str) -> tuple[list[dict], dict]:
    payload = api_get(
        token,
        {
            "dataset": "TaiwanStockPrice",
            "data_id": code,
            "start_date": start,
            "end_date": end,
        },
    )
    meta = {
        "status": payload.get("status"),
        "msg": payload.get("msg"),
        "dataset": "TaiwanStockPrice",
    }
    if payload.get("status") != 200:
        return [], meta
    rows = []
    for r in payload.get("data") or []:
        try:
            rows.append(
                {
                    "time": r["date"],  # YYYY-MM-DD for lightweight-charts
                    "open": float(r["open"]),
                    "high": float(r["max"]),
                    "low": float(r["min"]),
                    "close": float(r["close"]),
                    "volume": int(r.get("Trading_Volume") or 0),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    rows.sort(key=lambda x: x["time"])
    return rows, meta


def fetch_kbar_day(token: str, code: str, day: str) -> tuple[list[dict], dict]:
    """Minute bars for one day. TaiwanStockKBar is Sponsor-tier."""
    payload = api_get(
        token,
        {
            "dataset": "TaiwanStockKBar",
            "data_id": code,
            "start_date": day,
        },
    )
    meta = {
        "status": payload.get("status"),
        "msg": payload.get("msg"),
        "dataset": "TaiwanStockKBar",
        "day": day,
    }
    if payload.get("status") != 200:
        return [], meta
    rows = []
    for r in payload.get("data") or []:
        try:
            # minute often "09:01:00"; combine to unix for charts
            d = r["date"]
            m = r.get("minute") or r.get("time") or "09:00:00"
            if len(m) == 5:
                m = m + ":00"
            dt = datetime.strptime(f"{d} {m}", "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ8)
            rows.append(
                {
                    "time": int(dt.timestamp()),
                    "open": float(r["open"]),
                    "high": float(r["high"]),
                    "low": float(r["low"]),
                    "close": float(r["close"]),
                    "volume": float(r.get("volume") or 0),
                    "_iso": dt.isoformat(),
                }
            )
        except (KeyError, TypeError, ValueError):
            continue
    rows.sort(key=lambda x: x["time"])
    return rows, meta


def resample(minutes: list[dict], bucket_min: int) -> list[dict]:
    if not minutes:
        return []
    out = []
    bucket = None
    cur = None
    step = bucket_min * 60

    def flush():
        nonlocal cur
        if cur:
            out.append(cur)
            cur = None

    for r in minutes:
        t = int(r["time"])
        # align to bucket start in local sense via epoch floor
        b = t - (t % step)
        if bucket != b:
            flush()
            bucket = b
            cur = {
                "time": b,
                "open": r["open"],
                "high": r["high"],
                "low": r["low"],
                "close": r["close"],
                "volume": r["volume"],
            }
        else:
            cur["high"] = max(cur["high"], r["high"])
            cur["low"] = min(cur["low"], r["low"])
            cur["close"] = r["close"]
            cur["volume"] = (cur.get("volume") or 0) + (r.get("volume") or 0)
    flush()
    return out


def resolve_codes(args: argparse.Namespace) -> list[str]:
    codes: list[str] = []
    if args.watchlist:
        wp = Path(args.watchlist)
        if not wp.exists():
            raise SystemExit(f"watchlist not found: {wp}")
        for line in wp.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # allow "2330" or "2330,台積電"
            codes.append(line.split(",")[0].split()[0].strip().upper())
    if args.codes:
        for part in args.codes.replace(";", ",").split(","):
            part = part.strip().upper()
            if part:
                codes.append(part)
    if not codes:
        codes = [args.code.strip().upper()]
    # dedupe preserve order
    seen = set()
    out = []
    for c in codes:
        if c and c not in seen:
            seen.add(c)
            out.append(c)
    return out


def fetch_one(token: Optional[str], code: str, days: int, with_intraday: bool, intraday_days: int) -> dict[str, Any]:
    end = date.today()
    start = end - timedelta(days=days)
    daily, dmeta = fetch_daily(token, code, start.isoformat(), end.isoformat())
    print(f"{code} daily status={dmeta.get('status')} msg={dmeta.get('msg')!r} n={len(daily)}")

    doc: dict[str, Any] = {
        "meta": {
            "code": code,
            "source": "FinMind",
            "generated_at": datetime.now(TZ8).isoformat(timespec="seconds"),
            "daily_dataset": "TaiwanStockPrice",
            "daily_range": [start.isoformat(), end.isoformat()],
            "daily_status": dmeta,
            "note": "Separate from FundFlo; do not wire into refresh_daily slim.",
        },
        "daily": daily,
        "timeframes": {
            "1D": {"ok": bool(daily), "n": len(daily), "bars": daily},
        },
        "tier_notes": {},
    }

    if with_intraday:
        days_list = [r["time"] for r in daily[-intraday_days:]] if daily else []
        if not days_list:
            days_list = [(end - timedelta(days=i)).isoformat() for i in range(intraday_days)]
            days_list = list(reversed(days_list))
        all_m: list[dict] = []
        kbar_meta = []
        for day in days_list:
            rows, meta = fetch_kbar_day(token, code, day)
            kbar_meta.append(meta)
            print(f"{code} kbar {day} status={meta.get('status')} msg={meta.get('msg')!r} n={len(rows)}")
            all_m.extend(rows)
        doc["meta"]["kbar_attempts"] = kbar_meta
        any_ok = len(all_m) > 0
        doc["tier_notes"]["TaiwanStockKBar"] = {
            "docs_tier": "Sponsor",
            "got_rows": len(all_m),
            "blocked_hint": not any_ok,
        }
        if all_m:
            doc["timeframes"]["1m"] = {"ok": True, "n": len(all_m), "bars": all_m}
            for label, bm in [("5m", 5), ("15m", 15), ("1h", 60), ("4h", 240)]:
                bars = resample(all_m, bm)
                doc["timeframes"][label] = {"ok": True, "n": len(bars), "bars": bars}
        else:
            for label in ["1m", "5m", "15m", "1h", "4h"]:
                doc["timeframes"][label] = {
                    "ok": False,
                    "n": 0,
                    "bars": [],
                    "blocked": True,
                    "reason": (kbar_meta[-1].get("msg") if kbar_meta else "no kbar"),
                }

    OUT.mkdir(parents=True, exist_ok=True)
    out_path = OUT / f"{code}.json"
    out_path.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {out_path} bytes={out_path.stat().st_size}")
    return {
        "code": code,
        "ok": bool(daily),
        "daily_n": len(daily),
        "path": f"data/candles/{code}.json",
        "tfs": {k: {"ok": v.get("ok"), "n": v.get("n")} for k, v in doc["timeframes"].items()},
        "tier_notes": doc.get("tier_notes"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(
        description="FinMind candle cache (NOT FundFlo / refresh_daily). Token stays server-side."
    )
    ap.add_argument("--code", default="2330", help="single code if no watchlist/codes")
    ap.add_argument(
        "--codes",
        default="",
        help="comma-separated codes, e.g. 2330,2317,2454",
    )
    ap.add_argument(
        "--watchlist",
        default="",
        help="path to watchlist file (one code per line; # comments ok)",
    )
    ap.add_argument("--days", type=int, default=120, help="daily lookback calendar days")
    ap.add_argument("--with-intraday", action="store_true", help="try KBar (Sponsor; usually blocked on Free)")
    ap.add_argument("--intraday-days", type=int, default=5)
    ap.add_argument(
        "--sleep",
        type=float,
        default=1.0,
        help="seconds between codes (rate budget ~600/hr with token)",
    )
    args = ap.parse_args()

    token = load_token()
    print(f"auth={'token' if token else 'anon'}")
    codes = resolve_codes(args)
    print(f"codes n={len(codes)}: {', '.join(codes[:12])}{'…' if len(codes) > 12 else ''}")

    import time

    results = []
    for i, code in enumerate(codes):
        try:
            results.append(
                fetch_one(token, code, args.days, args.with_intraday, args.intraday_days)
            )
        except Exception as e:
            print(f"{code} ERR {type(e).__name__}: {e}")
            results.append({"code": code, "ok": False, "error": str(e)})
        if i + 1 < len(codes) and args.sleep > 0:
            time.sleep(args.sleep)

    latest = {
        "generated_at": datetime.now(TZ8).isoformat(timespec="seconds"),
        "auth": "token" if token else "anon",
        "n": len(results),
        "ok_n": sum(1 for r in results if r.get("ok")),
        "results": results,
        "note": "Separate from FundFlo slim; never put FINMIND_TOKEN in browser.",
    }
    (OUT / "latest.json").write_text(json.dumps(latest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT / 'latest.json'} ok={latest['ok_n']}/{latest['n']}")
    return 0 if latest["ok_n"] else 1


if __name__ == "__main__":
    sys.exit(main())
