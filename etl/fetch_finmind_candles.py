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


def load_token() -> Optional[str]:
    """Optional. Free-tier TaiwanStockPrice works anonymously (~300/hr); token ~600/hr.
    Rejects non-ASCII 'tokens' (users sometimes paste plan text with checkmarks).
    """
    t = (os.environ.get("FINMIND_TOKEN") or "").strip()
    if not t and SECRETS.exists():
        doc = json.loads(SECRETS.read_text())
        card = doc.get("card") or {}
        t = (card.get("FINMIND_TOKEN") or "").strip()
    if not t:
        return None
    ascii_t = "".join(ch for ch in t if ord(ch) < 128).strip()
    # real tokens are compact; plan-paste leftovers have spaces / are short alnum
    if " " in ascii_t or len(ascii_t) < 20:
        return None
    return ascii_t


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default="2330")
    ap.add_argument("--days", type=int, default=120, help="daily lookback calendar days")
    ap.add_argument("--with-intraday", action="store_true")
    ap.add_argument("--intraday-days", type=int, default=5)
    args = ap.parse_args()

    token = load_token()
    print(f"auth={'token' if token else 'anon'}")
    code = args.code.strip().upper()
    end = date.today()
    start = end - timedelta(days=args.days)

    daily, dmeta = fetch_daily(token, code, start.isoformat(), end.isoformat())
    print(f"daily status={dmeta.get('status')} msg={dmeta.get('msg')!r} n={len(daily)}")

    OUT.mkdir(parents=True, exist_ok=True)
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

    if args.with_intraday:
        # last N trading days from daily tail
        days = [r["time"] for r in daily[-args.intraday_days :]] if daily else []
        if not days:
            # fallback calendar
            days = [(end - timedelta(days=i)).isoformat() for i in range(args.intraday_days)]
            days = list(reversed(days))
        all_m: list[dict] = []
        kbar_meta = []
        for day in days:
            rows, meta = fetch_kbar_day(token, code, day)
            kbar_meta.append(meta)
            print(f"kbar {day} status={meta.get('status')} msg={meta.get('msg')!r} n={len(rows)}")
            all_m.extend(rows)
        doc["meta"]["kbar_attempts"] = kbar_meta
        sponsor_blocked = any(
            (m.get("status") not in (200, None))
            and (
                "sponsor" in str(m.get("msg") or "").lower()
                or "permission" in str(m.get("msg") or "").lower()
                or "權限" in str(m.get("msg") or "")
                or m.get("status") in (402, 403, 401)
            )
            for m in kbar_meta
        )
        any_ok = any(m.get("status") == 200 and True for m in kbar_meta)
        # refine: ok if we got rows
        any_ok = len(all_m) > 0
        doc["tier_notes"]["TaiwanStockKBar"] = {
            "docs_tier": "Sponsor",
            "got_rows": len(all_m),
            "blocked_hint": sponsor_blocked or (not any_ok),
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

    # slim latest pointer + per-code file (full bars for prototype)
    out_path = OUT / f"{code}.json"
    out_path.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    latest = {
        "code": code,
        "path": f"data/candles/{code}.json",
        "daily_n": len(daily),
        "tfs": {k: {"ok": v.get("ok"), "n": v.get("n")} for k, v in doc["timeframes"].items()},
        "tier_notes": doc.get("tier_notes"),
        "generated_at": doc["meta"]["generated_at"],
    }
    (OUT / "latest.json").write_text(json.dumps(latest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {out_path} bytes={out_path.stat().st_size}")
    print(f"wrote {OUT / 'latest.json'}")
    return 0 if daily else 1


if __name__ == "__main__":
    sys.exit(main())
