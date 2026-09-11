#!/usr/bin/env python3
"""Fetch TW stock candles from Fugle Market Data API → data/candles/ (NOT FundFlo).

Auth: FUGLE_API_KEY in env or /home/box/sand-data/box-secrets.json card.FUGLE_API_KEY
Header: X-API-KEY  (never put key in browser)

REST:
  GET https://api.fugle.tw/marketdata/v1.0/stock/historical/candles/{symbol}
  Query: from, to (range < 1 year), timeframe = 1|3|5|15|30|60|D|W|M

Usage:
  python3 etl/fetch_fugle_candles.py --code 2330 --timeframe 5 --days 5
  python3 etl/fetch_fugle_candles.py --code 2330 --timeframes 5,15,60,D --days 10
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "candles"
API = "https://api.fugle.tw/marketdata/v1.0/stock/historical/candles"
SECRETS = Path("/home/box/sand-data/box-secrets.json")
TZ8 = timezone(timedelta(hours=8))

# map our UI labels → Fugle timeframe query
TF_MAP = {
    "1m": "1",
    "3m": "3",
    "5m": "5",
    "15m": "15",
    "30m": "30",
    "60m": "60",
    "1h": "60",
    "1D": "D",
    "D": "D",
    "W": "W",
    "M": "M",
    "1": "1",
    "3": "3",
    "5": "5",
    "15": "15",
    "30": "30",
    "60": "60",
}


def load_key() -> str:
    k = (os.environ.get("FUGLE_API_KEY") or "").strip()
    if not k and SECRETS.exists():
        card = (json.loads(SECRETS.read_text()).get("card") or {})
        k = (card.get("FUGLE_API_KEY") or "").strip()
    k = "".join(ch for ch in k if ord(ch) < 128).strip()
    if not k or " " in k or len(k) < 8:
        raise SystemExit("FUGLE_API_KEY not set (env or box-secrets) / looks invalid")
    return k


def api_candles(key: str, symbol: str, tf: str, date_from: str, date_to: str) -> dict[str, Any]:
    q = urllib.parse.urlencode({"from": date_from, "to": date_to, "timeframe": tf})
    url = f"{API}/{urllib.parse.quote(symbol)}?{q}"
    req = urllib.request.Request(
        url,
        headers={
            "X-API-KEY": key,
            "Accept": "application/json",
            "User-Agent": "tw-moneyflow-candles-fugle/0.1",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        body = ""
        try:
            body = e.read().decode("utf-8", errors="replace")[:800]
        except Exception:
            pass
        raise RuntimeError(f"HTTP {e.code}: {body or e}") from e


def normalize_bars(payload: dict[str, Any], timeframe_label: str) -> list[dict[str, Any]]:
    """Fugle returns various shapes; normalize to lightweight-charts bars."""
    raw = payload.get("data") or payload.get("candles") or payload.get("ohlcv")
    if raw is None and isinstance(payload.get("symbol"), str):
        # sometimes top-level list missing — try common nest
        raw = payload.get("history") or []
    if not isinstance(raw, list):
        raw = []

    is_daily = timeframe_label in ("1D", "D", "W", "M")
    out: list[dict[str, Any]] = []
    for r in raw:
        if not isinstance(r, dict):
            continue
        # common field names
        ts = r.get("date") or r.get("time") or r.get("datetime") or r.get("timestamp")
        o = r.get("open")
        h = r.get("high")
        l = r.get("low")
        c = r.get("close")
        v = r.get("volume") or r.get("tradingVolume") or 0
        if ts is None or o is None or h is None or l is None or c is None:
            continue
        try:
            if is_daily:
                # date string YYYY-MM-DD
                if isinstance(ts, (int, float)):
                    dt = datetime.fromtimestamp(ts / (1000 if ts > 1e12 else 1), tz=TZ8)
                    time_val: Any = dt.strftime("%Y-%m-%d")
                else:
                    s = str(ts).replace("T", " ").split(" ")[0]
                    time_val = s[:10]
            else:
                if isinstance(ts, (int, float)):
                    sec = int(ts / 1000) if ts > 1e12 else int(ts)
                else:
                    s = str(ts).replace("Z", "")
                    if "T" in s or " " in s:
                        s2 = s.replace("T", " ")[:19]
                        dt = datetime.strptime(s2, "%Y-%m-%d %H:%M:%S").replace(tzinfo=TZ8)
                    else:
                        dt = datetime.strptime(s[:10], "%Y-%m-%d").replace(tzinfo=TZ8)
                    sec = int(dt.timestamp())
                time_val = sec
            out.append(
                {
                    "time": time_val,
                    "open": float(o),
                    "high": float(h),
                    "low": float(l),
                    "close": float(c),
                    "volume": float(v or 0),
                }
            )
        except (TypeError, ValueError):
            continue
    out.sort(key=lambda x: x["time"])
    return out


def fetch_tf(key: str, code: str, label: str, days: int) -> dict[str, Any]:
    fugle_tf = TF_MAP.get(label, label)
    end = date.today()
    start = end - timedelta(days=max(days, 1))
    # Fugle: range must be < 1 year
    if (end - start).days >= 365:
        start = end - timedelta(days=360)
    payload = api_candles(key, code, fugle_tf, start.isoformat(), end.isoformat())
    bars = normalize_bars(payload, label)
    return {
        "ok": bool(bars),
        "n": len(bars),
        "bars": bars,
        "fugle_timeframe": fugle_tf,
        "range": [start.isoformat(), end.isoformat()],
        "raw_keys": sorted(payload.keys()) if isinstance(payload, dict) else [],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--code", default="2330")
    ap.add_argument("--timeframe", default="5", help="single TF e.g. 5 / 5m / 15 / 60 / D")
    ap.add_argument("--timeframes", default="", help="comma list e.g. 5,15,60,D")
    ap.add_argument("--days", type=int, default=5, help="calendar lookback (minute: few sessions)")
    ap.add_argument("--sleep", type=float, default=0.4)
    args = ap.parse_args()

    key = load_key()
    print(f"fugle_key_ok len={len(key)}")
    code = args.code.strip().upper()
    labels = []
    if args.timeframes:
        labels = [x.strip() for x in args.timeframes.split(",") if x.strip()]
    else:
        labels = [args.timeframe.strip()]
    # normalize labels to UI style
    norm = []
    for lab in labels:
        if lab in TF_MAP:
            # prefer UI names
            if lab in ("5", "5m"):
                norm.append("5m")
            elif lab in ("15", "15m"):
                norm.append("15m")
            elif lab in ("60", "60m", "1h"):
                norm.append("1h")
            elif lab in ("D", "1D"):
                norm.append("1D")
            elif lab in ("1", "1m"):
                norm.append("1m")
            elif lab in ("30", "30m"):
                norm.append("30m")
            else:
                norm.append(lab)
        else:
            norm.append(lab)
    # dedupe
    seen = set()
    labels = []
    for x in norm:
        if x not in seen:
            seen.add(x)
            labels.append(x)

    OUT.mkdir(parents=True, exist_ok=True)
    results = {}
    for i, lab in enumerate(labels):
        try:
            block = fetch_tf(key, code, lab, args.days)
            print(f"{code} {lab} ok={block['ok']} n={block['n']} range={block['range']}")
            # write per-tf file
            path = OUT / f"{code}_{lab}.json"
            doc = {
                "meta": {
                    "code": code,
                    "source": "Fugle",
                    "timeframe": lab,
                    "generated_at": datetime.now(TZ8).isoformat(timespec="seconds"),
                    "note": "Server-side only API key; separate from FundFlo / FinMind daily cache.",
                    "range": block["range"],
                    "fugle_timeframe": block["fugle_timeframe"],
                    "raw_keys": block["raw_keys"],
                },
                "timeframes": {lab: {"ok": block["ok"], "n": block["n"], "bars": block["bars"]}},
            }
            # also mirror as daily list for 1D convenience
            if lab == "1D":
                doc["daily"] = block["bars"]
            path.write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            print(f"wrote {path} bytes={path.stat().st_size}")
            results[lab] = {"ok": block["ok"], "n": block["n"], "path": str(path.relative_to(ROOT))}
        except Exception as e:
            print(f"{code} {lab} ERR {type(e).__name__}: {e}")
            results[lab] = {"ok": False, "error": str(e)[:400]}
        if i + 1 < len(labels) and args.sleep > 0:
            time.sleep(args.sleep)

    # merge into combined code json if FinMind daily exists — additive timeframes
    combo_path = OUT / f"{code}.json"
    if combo_path.exists():
        try:
            combo = json.loads(combo_path.read_text(encoding="utf-8"))
        except Exception:
            combo = {"meta": {"code": code}, "timeframes": {}, "daily": []}
    else:
        combo = {"meta": {"code": code, "sources": []}, "timeframes": {}, "daily": []}
    combo.setdefault("meta", {})
    combo["meta"]["fugle_updated_at"] = datetime.now(TZ8).isoformat(timespec="seconds")
    combo["meta"]["fugle_results"] = results
    combo.setdefault("timeframes", {})
    for lab, info in results.items():
        if not info.get("ok"):
            continue
        p = ROOT / info["path"]
        part = json.loads(p.read_text(encoding="utf-8"))
        block = (part.get("timeframes") or {}).get(lab)
        if block:
            block = dict(block)
            block["source"] = "Fugle"
            combo["timeframes"][lab] = block
            if lab == "1D" and block.get("bars"):
                # don't clobber FinMind daily unless empty
                if not combo.get("daily"):
                    combo["daily"] = block["bars"]
                    combo["timeframes"]["1D"] = block
    combo_path.write_text(json.dumps(combo, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"merged {combo_path}")

    latest = {
        "generated_at": datetime.now(TZ8).isoformat(timespec="seconds"),
        "provider": "Fugle",
        "code": code,
        "results": results,
        "note": "FUGLE_API_KEY server-only; not in FundFlo slim.",
    }
    (OUT / "fugle_latest.json").write_text(json.dumps(latest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT / 'fugle_latest.json'}")
    ok = any(r.get("ok") for r in results.values())
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
