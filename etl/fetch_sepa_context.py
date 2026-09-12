#!/usr/bin/env python3
"""SEPA context fetch for the cockpit (FinMind only, keys in env — never in the browser).

Writes:
  data/candles/<code>.json       daily OHLCV (via same schema as fetch_finmind_candles)
  data/candles/0050.json         weighted-index daily (RS benchmark)
  data/candles/<code>_news.json  latest news titles (TaiwanStockNews)

Usage:
  python3 etl/fetch_sepa_context.py --code 2330 [--days 400]
"""
from __future__ import annotations

import argparse
import json
import os
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "candles"
API = "https://api.finmindtrade.com/api/v4/data"
TZ8 = timezone(timedelta(hours=8))
SECRETS = Path("/home/box/sand-data/box-secrets.json")


def load_token():
    cands = []
    env = (os.environ.get("FINMIND_TOKEN") or "").strip()
    if env:
        cands.append(env)
    if SECRETS.exists():
        try:
            card = (json.loads(SECRETS.read_text()) or {}).get("card") or {}
            sec = (card.get("FINMIND_TOKEN") or "").strip()
            if sec:
                cands.append(sec)
        except Exception:
            pass
    for t in cands:
        t2 = "".join(ch for ch in t if ord(ch) < 128).strip()
        if len(t2) >= 20 and " " not in t2:
            return t2
    return None


def api_get(token, params, timeout=60):
    q = urllib.parse.urlencode(params)
    headers = {"Accept": "application/json", "User-Agent": "tw-moneyflow-candles/0.1"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{API}?{q}", headers=headers, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def daily_rows(token, code, start, end):
    payload = api_get(token, {"dataset": "TaiwanStockPrice", "data_id": code,
                              "start_date": start, "end_date": end})
    rows = []
    for r in payload.get("data") or []:
        try:
            rows.append({
                "time": r["date"],
                "open": float(r["open"]),
                "high": float(r["max"]),
                "low": float(r["min"]),
                "close": float(r["close"]),
                "volume": int(r.get("Trading_Volume") or 0),
            })
        except (KeyError, TypeError, ValueError):
            continue
    rows.sort(key=lambda x: x["time"])
    return rows, payload.get("status")


def news_items(token, code, limit=10, days=5):
    # TaiwanStockNews returns one day per call; end_date must be omitted.
    items, seen = [], set()
    end = date.today()
    for i in range(days):
        d = (end - timedelta(days=i)).isoformat()
        try:
            payload = api_get(token, {"dataset": "TaiwanStockNews", "data_id": code, "start_date": d})
        except Exception:
            continue
        for r in payload.get("data") or []:
            if not isinstance(r, dict):
                continue
            t = str(r.get("title") or "").strip()
            dt = str(r.get("date") or r.get("published_date") or "")[:10]
            if t and t not in seen:
                seen.add(t)
                items.append({"date": dt, "title": t})
            if len(items) >= limit:
                return items
    return items


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default="2330")
    ap.add_argument("--days", type=int, default=400)
    args = ap.parse_args()
    token = load_token()
    print(f"auth={'token' if token else 'anon'}")

    code = args.code.strip().upper()
    end = date.today()
    start = end - timedelta(days=args.days)
    OUT.mkdir(parents=True, exist_ok=True)

    for c in sorted({code, "0050"}):
        rows, st = daily_rows(token, c, start.isoformat(), end.isoformat())
        doc = {
            "meta": {"code": c, "source": "FinMind", "daily_dataset": "TaiwanStockPrice",
                     "daily_range": [start.isoformat(), end.isoformat()],
                     "status": st,
                     "generated_at": datetime.now(TZ8).isoformat(timespec="seconds"),
                     "note": "Cockpit cache; separate from FundFlo slim."},
            "daily": rows,
        }
        (OUT / f"{c}.json").write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"{c}: status={st} n={len(rows)}")

    items = news_items(token, code)
    (OUT / f"{code}_news.json").write_text(
        json.dumps({"code": code, "items": items}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"news n={len(items)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
