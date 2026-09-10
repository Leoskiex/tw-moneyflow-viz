#!/usr/bin/env python3
"""Build FundFlo feature JSON from curated (+ optional MI_INDEX closes).

Reads data/curated/*.json, writes:
  data/fundflo/by_date/YYYY-MM-DD.json
  data/fundflo/latest.json
  data/fundflo/fixture.json  (tiny synthetic if curated empty / --fixture-only)

Unit caveat: curated foreign_net is 千張 (1e6 股). See docs/FUNDFLO_CONTRACT.md.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from fundflo_model import (  # noqa: E402
    WINDOW,
    enrich_day_metrics,
    foreign_flow_yi_from_net,
    shares_from_foreign_net_qianzhang,
)

CURATED_DIR = ROOT / "data" / "curated"
OUT_DIR = ROOT / "data" / "fundflo"
BY_DATE = OUT_DIR / "by_date"
ETF_HOLDINGS = ROOT / "data" / "etf" / "00981a" / "holdings"


def _num(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x) if (x == x and abs(x) != float("inf")) else None
    s = str(x).strip().replace(",", "").replace("%", "")
    if not s or s in {"--", "---", "nan", "NaN"}:
        return None
    # strip +/- markers that aren't part of the number
    s = s.replace("＋", "+").replace("－", "-")
    try:
        return float(s)
    except ValueError:
        return None


def discover_raw_dir(cli: Optional[str]) -> Optional[Path]:
    candidates = []
    if cli:
        candidates.append(Path(cli))
    env = os.environ.get("TWSE_RAW_DIR")
    if env:
        candidates.append(Path(env))
    # optional box / sibling layouts — never required
    candidates.extend(
        [
            Path("/workspace/twse-trading/raw"),
            ROOT.parent.parent / "twse-trading" / "raw",
            ROOT.parent / "twse-trading" / "raw",
        ]
    )
    for p in candidates:
        if p and p.is_dir():
            return p
    return None


def load_mi_index_prices(raw_dir: Path, date: str) -> Dict[str, Dict[str, float]]:
    """code -> {close, avg, amount_yi} from MI_INDEX daily table."""
    path = raw_dir / date / "MI_INDEX.json"
    if not path.exists():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: Dict[str, Dict[str, float]] = {}
    for table in doc.get("tables") or []:
        fields = table.get("fields") or []
        if "證券代號" not in fields or "收盤價" not in fields:
            continue
        fi = {name: i for i, name in enumerate(fields)}
        for row in table.get("data") or []:
            if not row:
                continue
            code = str(row[fi["證券代號"]]).strip()
            if not re.match(r"^\d{4}", code):
                continue
            close = _num(row[fi["收盤價"]])
            shares = _num(row[fi["成交股數"]]) if "成交股數" in fi else None
            amount = _num(row[fi["成交金額"]]) if "成交金額" in fi else None
            avg = None
            if shares and shares > 0 and amount is not None:
                avg = amount / shares
            price = avg if avg and avg > 0 else close
            if price is None or price <= 0:
                continue
            out[code] = {
                "close": close or price,
                "avg": avg or price,
                "amount_yi": (amount / 1e8) if amount is not None else None,
            }
        break
    return out


def load_tpex_prices(raw_dir: Path, date: str) -> Dict[str, Dict[str, float]]:
    """Best-effort TPEx closes if TPEX_QUOTE.json present."""
    path = raw_dir / date / "TPEX_QUOTE.json"
    if not path.exists():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    out: Dict[str, Dict[str, float]] = {}
    tables = doc if isinstance(doc, list) else doc.get("tables") or doc.get("aaData") or []
    # heterogeneous; try common shapes
    if isinstance(doc, dict) and "data" in doc and isinstance(doc["data"], list):
        tables = [{"data": doc["data"], "fields": doc.get("fields")}]
    for table in tables if isinstance(tables, list) else []:
        if not isinstance(table, dict):
            continue
        fields = table.get("fields") or []
        data = table.get("data") or []
        # guess indices
        code_i = next((i for i, f in enumerate(fields) if "代號" in str(f) or "代码" in str(f)), 0)
        close_i = next((i for i, f in enumerate(fields) if "收盤" in str(f) or "收盘" in str(f)), None)
        if close_i is None:
            continue
        for row in data:
            if not row or len(row) <= max(code_i, close_i):
                continue
            code = str(row[code_i]).strip()
            close = _num(row[close_i])
            if re.match(r"^\d{4}", code) and close and close > 0:
                out[code] = {"close": close, "avg": close, "amount_yi": None}
    return out


def load_etf_share_deltas() -> Dict[str, Dict[str, float]]:
    """date -> {code: share_delta} from 00981a holdings snapshots."""
    by_date: Dict[str, Dict[str, float]] = {}
    if not ETF_HOLDINGS.is_dir():
        # try latest only
        latest = ROOT / "data" / "etf" / "00981a" / "latest.json"
        if latest.exists():
            try:
                doc = json.loads(latest.read_text(encoding="utf-8"))
                dt = doc.get("date")
                holds = doc.get("holdings") or []
                if dt:
                    by_date[dt] = {
                        str(h["code"]): float(h.get("share_delta") or 0.0)
                        for h in holds
                        if h.get("code")
                    }
            except Exception:
                pass
        return by_date
    for path in sorted(ETF_HOLDINGS.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        dt = doc.get("date") or path.stem
        holds = doc.get("holdings") or []
        by_date[dt] = {
            str(h["code"]): float(h.get("share_delta") or 0.0) for h in holds if h.get("code")
        }
    return by_date


def curated_dates() -> List[str]:
    if not CURATED_DIR.is_dir():
        return []
    dates = []
    for p in sorted(CURATED_DIR.glob("*.json")):
        if p.name == "index.json":
            continue
        if re.match(r"^\d{4}-\d{2}-\d{2}\.json$", p.name):
            dates.append(p.stem)
    return dates


def stock_price(stock: dict, px: Optional[Dict[str, float]]) -> Optional[float]:
    for key in ("avg_price", "average", "avg", "close", "adj_close", "adjustedClose"):
        v = _num(stock.get(key))
        if v and v > 0:
            return v
    if px:
        return px.get("avg") or px.get("close")
    return None


def build_synthetic_fixture() -> dict:
    """Tiny 6-day / 4-stock fixture so fund-flow.html renders without curated."""
    codes = [
        ("2330", "台積電"),
        ("2317", "鴻海"),
        ("2454", "聯發科"),
        ("2881", "富邦金"),
    ]
    base_flows = {
        "2330": [2.0, 2.5, 3.0, 1.5, 4.0, 3.5],
        "2317": [-1.0, -0.5, 0.5, 1.0, 0.2, -0.3],
        "2454": [0.5, 0.8, 1.2, 0.9, 1.5, 1.1],
        "2881": [-0.2, 0.1, -0.4, -0.6, 0.3, 0.5],
    }
    closes = {
        "2330": [900, 910, 920, 915, 930, 940],
        "2317": [100, 101, 102, 103, 104, 105],
        "2454": [1200, 1210, 1190, 1220, 1230, 1240],
        "2881": [70, 71, 69, 68, 70, 72],
    }
    dates = [f"2026-09-0{i}" for i in range(1, 7)]
    by_code_hist: Dict[str, List[dict]] = {c: [] for c, _ in codes}
    for di, dt in enumerate(dates):
        for code, name in codes:
            foreign = base_flows[code][di]
            etf = 0.1 if code == "2330" else 0.0
            close = closes[code][di]
            shares = foreign * 1e8 / close  # invert flow_yi = shares*px/1e8
            by_code_hist[code].append(
                {
                    "date": dt,
                    "code": code,
                    "name": name,
                    "foreign_flow_yi": foreign,
                    "etf_flow_yi": etf,
                    "combined_flow_yi": foreign + etf,
                    "shares": shares,
                    "close": close,
                    "is_common": True,
                    "topic": "fixture",
                }
            )
    stocks_out = []
    for code, name in codes:
        enriched = enrich_day_metrics(by_code_hist[code])
        last = enriched[-1]
        stocks_out.append(last)
    # series payload for UI playback
    series = []
    for code, name in codes:
        series.append(
            {
                "code": code,
                "name": name,
                "days": enrich_day_metrics(by_code_hist[code]),
            }
        )
    return {
        "meta": {
            "date": dates[-1],
            "dates": dates,
            "window": WINDOW,
            "generated_by": "build_fundflo_features.py",
            "synthetic": True,
            "note": "synthetic fixture — curated empty or --fixture-only",
            "unit_foreign_flow": "億元",
            "unit_shares": "股",
            "unit_curated_foreign_net": "千張 (1千張=1e6股)",
            "conversion": "foreign_flow_yi = foreign_net * price / 100",
        },
        "stocks": stocks_out,
        "series": series,
    }


def build(raw_dir: Optional[Path], max_dates: Optional[int] = None) -> Tuple[dict, List[str]]:
    dates = curated_dates()
    if max_dates:
        dates = dates[-max_dates:]
    if not dates:
        fix = build_synthetic_fixture()
        return fix, []

    etf_deltas = load_etf_share_deltas()
    # Accumulate per-code history
    hist: Dict[str, List[dict]] = defaultdict(list)
    meta_names: Dict[str, dict] = {}
    price_hits = 0
    price_miss = 0

    for dt in dates:
        path = CURATED_DIR / f"{dt}.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        px_map: Dict[str, Dict[str, float]] = {}
        if raw_dir:
            px_map.update(load_mi_index_prices(raw_dir, dt))
            for k, v in load_tpex_prices(raw_dir, dt).items():
                px_map.setdefault(k, v)
        etf_today = etf_deltas.get(dt) or {}

        for stock in doc.get("stocks") or []:
            if stock.get("is_etf") or stock.get("is_leverage"):
                continue
            if stock.get("is_common") is False:
                continue
            code = str(stock.get("code") or "").strip()
            if not re.match(r"^\d{4}", code):
                continue
            # skip ETF-like codes 00xx unless common equity
            if code.startswith("00") and not stock.get("is_common"):
                continue

            foreign_net = _num(stock.get("foreign_net")) or 0.0
            px = stock_price(stock, px_map.get(code))
            shares = shares_from_foreign_net_qianzhang(foreign_net)
            if px is not None:
                foreign_yi = foreign_flow_yi_from_net(foreign_net, px)
                price_hits += 1
            else:
                foreign_yi = None
                price_miss += 1

            share_delta = etf_today.get(code)
            if share_delta is not None and px is not None:
                etf_yi = share_delta * px / 1e8
            else:
                etf_yi = 0.0

            day = {
                "date": dt,
                "code": code,
                "name": stock.get("name") or code,
                "foreign_net_qianzhang": foreign_net,
                "shares": shares,
                "close": px,
                "foreign_flow_yi": None if foreign_yi is None else round(foreign_yi, 6),
                "etf_flow_yi": round(etf_yi, 6),
                "combined_flow_yi": None
                if foreign_yi is None
                else round(foreign_yi + etf_yi, 6),
                "change": _num(stock.get("change")),
                "amount": _num(stock.get("amount")),
                "topic": stock.get("topicName") or stock.get("topic"),
                "group": stock.get("group"),
                "market": stock.get("market"),
                "is_common": bool(stock.get("is_common", True)),
            }
            hist[code].append(day)
            meta_names[code] = {
                "name": day["name"],
                "topic": day["topic"],
                "group": day["group"],
                "market": day["market"],
            }

    # Enrich + emit by_date from last snapshot of each code's series
    series = []
    by_date_stocks: Dict[str, List[dict]] = defaultdict(list)
    for code, days in hist.items():
        enriched = enrich_day_metrics(days)
        series.append(
            {
                "code": code,
                "name": meta_names[code]["name"],
                "topic": meta_names[code].get("topic"),
                "group": meta_names[code].get("group"),
                "market": meta_names[code].get("market"),
                "days": enriched,
            }
        )
        for row in enriched:
            by_date_stocks[row["date"]].append(
                {
                    "code": row["code"],
                    "name": row["name"],
                    "foreign_flow_yi": row.get("foreign_flow_yi"),
                    "etf_flow_yi": row.get("etf_flow_yi", 0.0),
                    "combined_flow_yi": row.get("combined_flow_yi"),
                    "rolling_foreign_5d_yi": row.get("rolling_foreign_5d_yi"),
                    "momentum_foreign_5d_yi": row.get("momentum_foreign_5d_yi"),
                    "rolling_combined_5d_yi": row.get("rolling_combined_5d_yi"),
                    "momentum_combined_5d_yi": row.get("momentum_combined_5d_yi"),
                    "rolling_ret_5d": row.get("rolling_ret_5d"),
                    "shares": row.get("shares"),
                    "close": row.get("close"),
                    "topic": row.get("topic"),
                    "group": row.get("group"),
                    "market": row.get("market"),
                }
            )

    latest_date = dates[-1]
    latest_stocks = by_date_stocks.get(latest_date) or []
    # sort by |rolling_foreign| desc for convenience
    latest_stocks = sorted(
        latest_stocks,
        key=lambda s: abs(s.get("rolling_foreign_5d_yi") or s.get("foreign_flow_yi") or 0),
        reverse=True,
    )

    latest = {
        "meta": {
            "date": latest_date,
            "dates": dates,
            "n_stocks": len(latest_stocks),
            "n_series": len(series),
            "window": WINDOW,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generated_by": "build_fundflo_features.py",
            "raw_dir": str(raw_dir) if raw_dir else None,
            "price_hits": price_hits,
            "price_miss": price_miss,
            "unit_foreign_flow": "億元",
            "unit_shares": "股",
            "unit_curated_foreign_net": "千張 (1千張=1e6股)",
            "conversion": "foreign_flow_yi = foreign_net * price / 100  (= shares*price/1e8)",
            "etf_note": "etf_flow_yi from 00981A share_delta*price/1e8 when holdings exist else 0",
            "contract": "docs/FUNDFLO_CONTRACT.md",
        },
        "stocks": latest_stocks,
        "series": series,
    }
    return latest, dates



def _compact_series(series: List[dict], keep_dates: int = 10, top_n: int = 40) -> List[dict]:
    """Keep last keep_dates days; include codes that ranked top_n by |rolling_foreign| any day."""
    if not series:
        return []
    all_dates = sorted({d["date"] for s in series for d in (s.get("days") or [])})
    keep = set(all_dates[-keep_dates:])
    hot: set = set()
    for dt in keep:
        scored = []
        for s in series:
            for row in s.get("days") or []:
                if row.get("date") != dt:
                    continue
                v = row.get("rolling_foreign_5d_yi")
                if v is None:
                    v = row.get("foreign_flow_yi")
                if v is None:
                    continue
                scored.append((abs(float(v)), s["code"]))
        scored.sort(reverse=True)
        for _, code in scored[:top_n]:
            hot.add(code)
    out = []
    for s in series:
        if s["code"] not in hot:
            continue
        days = [d for d in (s.get("days") or []) if d.get("date") in keep]
        if len(days) < WINDOW:
            continue
        out.append({**s, "days": days})
    return out


def write_outputs(latest: dict, dates: List[str], write_by_date: bool = True) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    BY_DATE.mkdir(parents=True, exist_ok=True)

    # slim latest without full series for Pages weight? Keep series — UI needs it.
    # Also write a lite latest without series.
    lite = {k: v for k, v in latest.items() if k != "series"}
    (OUT_DIR / "latest.json").write_text(
        json.dumps(lite, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    # Compact playback series: last N dates × stocks that hit top-|rolling| on any day
    series_top = _compact_series(latest.get("series") or [], keep_dates=10, top_n=40)
    (OUT_DIR / "series_top.json").write_text(
        json.dumps(
            {"meta": {**latest["meta"], "series_mode": "top", "keep_dates": 10, "top_n": 40},
             "series": series_top},
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )

    if latest["meta"].get("synthetic"):
        (OUT_DIR / "fixture.json").write_text(
            json.dumps(latest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # also as by_date
        dt = latest["meta"]["date"]
        (BY_DATE / f"{dt}.json").write_text(
            json.dumps(
                {"meta": latest["meta"], "stocks": latest["stocks"]},
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return

    if write_by_date:
        # rebuild by_date map from series
        by_date: Dict[str, List[dict]] = defaultdict(list)
        for s in latest.get("series") or []:
            for row in s.get("days") or []:
                by_date[row["date"]].append(
                    {
                        "code": row["code"],
                        "name": row.get("name") or s.get("name"),
                        "foreign_flow_yi": row.get("foreign_flow_yi"),
                        "etf_flow_yi": row.get("etf_flow_yi", 0.0),
                        "combined_flow_yi": row.get("combined_flow_yi"),
                        "rolling_foreign_5d_yi": row.get("rolling_foreign_5d_yi"),
                        "momentum_foreign_5d_yi": row.get("momentum_foreign_5d_yi"),
                        "rolling_combined_5d_yi": row.get("rolling_combined_5d_yi"),
                        "momentum_combined_5d_yi": row.get("momentum_combined_5d_yi"),
                        "rolling_ret_5d": row.get("rolling_ret_5d"),
                        "shares": row.get("shares"),
                        "close": row.get("close"),
                        "topic": row.get("topic"),
                        "group": row.get("group"),
                        "market": row.get("market"),
                    }
                )
        for dt, stocks in by_date.items():
            stocks = sorted(
                stocks,
                key=lambda s: abs(s.get("rolling_foreign_5d_yi") or 0),
                reverse=True,
            )
            payload = {
                "meta": {
                    "date": dt,
                    "n_stocks": len(stocks),
                    "window": WINDOW,
                    "contract": "docs/FUNDFLO_CONTRACT.md",
                },
                "stocks": stocks,
            }
            (BY_DATE / f"{dt}.json").write_text(
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                encoding="utf-8",
            )

    # always keep a small fixture for demos / empty clones
    fix = build_synthetic_fixture()
    (OUT_DIR / "fixture.json").write_text(
        json.dumps(fix, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw-dir", default=None, help="TWSE raw day dumps (MI_INDEX)")
    ap.add_argument("--fixture-only", action="store_true")
    ap.add_argument("--max-dates", type=int, default=None)
    ap.add_argument("--skip-by-date", action="store_true")
    args = ap.parse_args()

    if args.fixture_only:
        latest = build_synthetic_fixture()
        write_outputs(latest, latest["meta"]["dates"])
        print(f"wrote synthetic fixture → {OUT_DIR}")
        return

    raw = discover_raw_dir(args.raw_dir)
    print(f"curated={CURATED_DIR} raw={raw}")
    latest, dates = build(raw, max_dates=args.max_dates)
    write_outputs(latest, dates, write_by_date=not args.skip_by_date)
    m = latest["meta"]
    print(
        f"date={m.get('date')} stocks={m.get('n_stocks')} series={m.get('n_series')} "
        f"price_hits={m.get('price_hits')} price_miss={m.get('price_miss')} → {OUT_DIR}"
    )


if __name__ == "__main__":
    main()
