#!/usr/bin/env python3
"""Build FundFlo feature JSON from curated (+ optional MI_INDEX closes).

Reads data/curated/*.json (or TW_VIZ curated), writes:
  data/fundflo/latest.json
  data/fundflo/series_top.json
  data/fundflo/fixture.json
  data/fundflo/by_date/YYYY-MM-DD.json (optional)

Modes covered: foreign | etf | combined | turnover
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

OUT_DIR = ROOT / "data" / "fundflo"
BY_DATE = OUT_DIR / "by_date"

# Name tokens that are not ordinary common shares (FundFlo turnover exclusion)
_NON_COMMON_NAME = re.compile(
    r"(ETF|ETN|權證|牛證|熊證|特別股|特別|存託憑證|TDR|指數|反向|槓桿)",
    re.I,
)


def discover_curated_dir(cli: Optional[str] = None) -> Path:
    """Prefer repo data/curated if present; else env / box TW_VIZ path."""
    candidates: List[Path] = []
    if cli:
        candidates.append(Path(cli))
    for env in ("TW_VIZ_CURATED", "TW_CURATED_DIR", "CURATED_DIR"):
        v = os.environ.get(env)
        if v:
            candidates.append(Path(v))
    candidates.extend(
        [
            ROOT / "data" / "curated",
            Path("/workspace/tw-moneyflow-viz/data/curated"),
            ROOT.parent.parent / "tw-moneyflow-viz" / "data" / "curated",
        ]
    )
    for p in candidates:
        if p and p.is_dir() and any(p.glob("????-??-??.json")):
            return p
    return ROOT / "data" / "curated"


CURATED_DIR = discover_curated_dir()


def _num(x: Any) -> Optional[float]:
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x) if (x == x and abs(x) != float("inf")) else None
    s = str(x).strip().replace(",", "").replace("%", "")
    if not s or s in {"--", "---", "nan", "NaN"}:
        return None
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


def discover_etf_roots() -> List[Path]:
    roots: List[Path] = []
    for p in (
        ROOT / "data" / "etf",
        Path("/workspace/tw-moneyflow-viz/data/etf"),
    ):
        if p.is_dir() and p not in roots:
            roots.append(p)
    return roots


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
    if isinstance(doc, dict) and "data" in doc and isinstance(doc["data"], list):
        tables = [{"data": doc["data"], "fields": doc.get("fields")}]
    for table in tables if isinstance(tables, list) else []:
        if not isinstance(table, dict):
            continue
        fields = table.get("fields") or []
        data = table.get("data") or []
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


def _read_holdings_doc(path: Path) -> Optional[Tuple[str, List[dict]]]:
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    dt = doc.get("date")
    if not dt and re.match(r"^\d{4}-\d{2}-\d{2}$", path.stem):
        dt = path.stem
    holds = doc.get("holdings") or []
    if not dt or not isinstance(holds, list):
        return None
    return str(dt), holds


def _shares_map(holds: List[dict]) -> Dict[str, float]:
    out: Dict[str, float] = {}
    for h in holds:
        code = str(h.get("code") or "").strip()
        if not code:
            continue
        share = _num(h.get("share"))
        if share is None:
            continue
        out[code] = float(share)
    return out


def _deltas_from_holds(holds: List[dict]) -> Optional[Dict[str, float]]:
    """Return code->share_delta if any holding carries share_delta."""
    if not any(h.get("share_delta") is not None for h in holds):
        return None
    out: Dict[str, float] = {}
    for h in holds:
        code = str(h.get("code") or "").strip()
        if not code:
            continue
        out[code] = float(_num(h.get("share_delta")) or 0.0)
    return out


def load_etf_share_deltas() -> Tuple[Dict[str, Dict[str, float]], List[str], Dict[str, Any]]:
    """Scan data/etf/*/ for ANY active ETF; sum share_delta across ETFs.

    Returns (date -> {stock_code: share_delta}, active_etfs_used, stats).
    When share_delta missing, derive from consecutive holdings share snapshots.
    """
    # etf_code -> date -> holdings list (prefer richest)
    by_etf_docs: Dict[str, Dict[str, List[dict]]] = defaultdict(dict)
    active: List[str] = []

    for root in discover_etf_roots():
        for etf_dir in sorted(root.iterdir()):
            if not etf_dir.is_dir():
                continue
            etf_code = etf_dir.name.upper() if etf_dir.name.lower() == etf_dir.name else etf_dir.name
            # normalize display code
            etf_code = etf_dir.name
            paths: List[Path] = []
            holdings_dir = etf_dir / "holdings"
            if holdings_dir.is_dir():
                paths.extend(sorted(holdings_dir.glob("*.json")))
            for name in ("holdings_latest.json", "latest.json"):
                p = etf_dir / name
                if p.exists():
                    paths.append(p)
            paths.extend(sorted(etf_dir.glob("????-??-??.json")))
            found = False
            for path in paths:
                parsed = _read_holdings_doc(path)
                if not parsed:
                    continue
                dt, holds = parsed
                # Prefer docs that already include share_delta
                prev = by_etf_docs[etf_code].get(dt)
                if prev is None or (
                    _deltas_from_holds(holds) is not None and _deltas_from_holds(prev) is None
                ):
                    by_etf_docs[etf_code][dt] = holds
                found = True
            if found and etf_code not in active:
                active.append(etf_code)

    # date -> stock -> summed delta
    summed: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    etf_day_nonzero = 0
    etf_stock_day_nonzero = 0

    for etf_code, by_date in by_etf_docs.items():
        dates = sorted(by_date.keys())
        prev_shares: Optional[Dict[str, float]] = None
        for dt in dates:
            holds = by_date[dt]
            deltas = _deltas_from_holds(holds)
            cur_shares = _shares_map(holds)
            if deltas is None:
                deltas = {}
                if prev_shares is not None:
                    codes = set(prev_shares) | set(cur_shares)
                    for code in codes:
                        deltas[code] = cur_shares.get(code, 0.0) - prev_shares.get(code, 0.0)
                # else first snapshot: no delta (avoid treating full book as buy)
            day_has = False
            for code, delta in deltas.items():
                if not delta:
                    continue
                summed[dt][code] += float(delta)
                etf_stock_day_nonzero += 1
                day_has = True
            if day_has:
                etf_day_nonzero += 1
            prev_shares = cur_shares or prev_shares

    # freeze nested dicts
    out = {dt: dict(m) for dt, m in summed.items()}
    stats = {
        "active_etfs_used": active,
        "etf_dates": sorted(out.keys()),
        "etf_day_nonzero": etf_day_nonzero,
        "etf_stock_day_nonzero": etf_stock_day_nonzero,
        "etf_roots": [str(p) for p in discover_etf_roots()],
    }
    return out, active, stats


def curated_dates(curated_dir: Path) -> List[str]:
    if not curated_dir.is_dir():
        return []
    dates = []
    for p in sorted(curated_dir.glob("*.json")):
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


def is_common_stock(stock: dict) -> bool:
    """Exclude ETF/ETN/warrant/pref/TDR like FundFlo turnover filter."""
    if stock.get("is_etf") or stock.get("is_leverage"):
        return False
    if stock.get("is_common") is False:
        return False
    code = str(stock.get("code") or "").strip()
    name = str(stock.get("name") or "")
    if not re.match(r"^\d{4}", code):
        return False
    # bare 00xx ETF/ETN codes unless explicitly marked common
    if re.match(r"^00\d{2}", code) and not stock.get("is_common"):
        return False
    if _NON_COMMON_NAME.search(name):
        return False
    # preferred share letter suffixes common on TW: 2330A etc. kept if is_common
    if re.search(r"[A-Z]$", code) and ("特別" in name or "優先" in name):
        return False
    return True


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
    amounts = {
        "2330": [500, 520, 480, 600, 550, 700],
        "2317": [80, 90, 85, 70, 95, 100],
        "2454": [120, 130, 110, 140, 150, 145],
        "2881": [40, 42, 38, 35, 44, 50],
    }
    dates = [f"2026-09-0{i}" for i in range(1, 7)]
    by_code_hist: Dict[str, List[dict]] = {c: [] for c, _ in codes}
    for di, dt in enumerate(dates):
        day_amts = {c: amounts[c][di] for c, _ in codes}
        total_amt = sum(day_amts.values()) or 1.0
        for code, name in codes:
            foreign = base_flows[code][di]
            etf = 0.1 if code == "2330" else 0.0
            close = closes[code][di]
            shares = foreign * 1e8 / close
            amount = amounts[code][di]
            prior = amounts[code][max(0, di - 5) : di]
            average5 = sum(prior) / len(prior) if len(prior) == 5 else None
            change_pct = ((amount / average5) - 1) * 100 if average5 else None
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
                    "adjustedClose": close,
                    "change": (close / closes[code][di - 1] - 1) * 100 if di else 0.0,
                    "amount": amount,
                    "average5": None if average5 is None else round(average5, 6),
                    "change_pct": None if change_pct is None else round(change_pct, 6),
                    "turnover_change": None if change_pct is None else round(change_pct, 6),
                    "market_share": round(amount / total_amt * 100, 6),
                    "is_common": True,
                    "topic": "fixture",
                }
            )
    stocks_out = []
    for code, name in codes:
        enriched = enrich_day_metrics(by_code_hist[code])
        stocks_out.append(enriched[-1])
    series = []
    for code, name in codes:
        series.append({"code": code, "name": name, "days": enrich_day_metrics(by_code_hist[code])})
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
            "active_etfs_used": ["00981a"],
            "modes": ["foreign", "etf", "combined", "turnover"],
        },
        "stocks": stocks_out,
        "series": series,
    }


def _attach_turnover_for_date(
    day_rows: List[dict],
    hist: Dict[str, List[dict]],
) -> None:
    """Mutate day_rows with average5 / change_pct / market_share / daily_ret."""
    total = 0.0
    for row in day_rows:
        amt = _num(row.get("amount"))
        if amt is not None and amt > 0:
            total += amt
    if total <= 0:
        total = 1.0
    for row in day_rows:
        code = row["code"]
        amount = _num(row.get("amount"))
        prior = hist.get(code) or []
        prior_amts = [_num(d.get("amount")) for d in prior[-WINDOW:]]
        average5 = None
        change_pct = None
        if len(prior_amts) == WINDOW and all(v is not None for v in prior_amts):
            average5 = sum(prior_amts) / float(WINDOW)  # type: ignore[arg-type]
            if amount is not None and average5:
                change_pct = (amount / average5 - 1.0) * 100.0
        row["average5"] = None if average5 is None else round(average5, 6)
        row["change_pct"] = None if change_pct is None else round(change_pct, 6)
        row["turnover_change"] = row["change_pct"]
        row["market_share"] = None if amount is None else round(amount / total * 100.0, 6)
        # daily_ret from curated change% (already pct)
        ch = _num(row.get("change"))
        row["daily_ret"] = ch


def build(
    raw_dir: Optional[Path],
    max_dates: Optional[int] = None,
    curated_dir: Optional[Path] = None,
) -> Tuple[dict, List[str]]:
    curated = curated_dir or CURATED_DIR
    dates = curated_dates(curated)
    if max_dates:
        dates = dates[-max_dates:]
    if not dates:
        fix = build_synthetic_fixture()
        return fix, []

    etf_deltas, active_etfs, etf_stats = load_etf_share_deltas()
    hist: Dict[str, List[dict]] = defaultdict(list)
    meta_names: Dict[str, dict] = {}
    price_hits = 0
    price_miss = 0
    etf_flow_nonzero_days = 0  # stock-days with nonzero etf_flow_yi

    for dt in dates:
        path = curated / f"{dt}.json"
        doc = json.loads(path.read_text(encoding="utf-8"))
        px_map: Dict[str, Dict[str, float]] = {}
        if raw_dir:
            px_map.update(load_mi_index_prices(raw_dir, dt))
            for k, v in load_tpex_prices(raw_dir, dt).items():
                px_map.setdefault(k, v)
        etf_today = etf_deltas.get(dt) or {}
        day_rows: List[dict] = []

        for stock in doc.get("stocks") or []:
            if not is_common_stock(stock):
                continue
            code = str(stock.get("code") or "").strip()

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
            if share_delta is not None and px is not None and share_delta != 0:
                etf_yi = share_delta * px / 1e8
            elif share_delta is not None and px is not None:
                etf_yi = 0.0
            else:
                etf_yi = 0.0
            if etf_yi:
                etf_flow_nonzero_days += 1

            amount = _num(stock.get("amount"))
            day = {
                "date": dt,
                "code": code,
                "name": stock.get("name") or code,
                "foreign_net_qianzhang": foreign_net,
                "shares": shares,
                "close": px,
                "adjustedClose": px,
                "foreign_flow_yi": None if foreign_yi is None else round(foreign_yi, 6),
                "etf_flow_yi": round(etf_yi, 6),
                "combined_flow_yi": None
                if foreign_yi is None
                else round(foreign_yi + etf_yi, 6),
                "change": _num(stock.get("change")),
                "amount": amount,
                "topic": stock.get("topicName") or stock.get("topic"),
                "group": stock.get("group"),
                "market": stock.get("market"),
                "is_common": True,
            }
            day_rows.append(day)
            meta_names[code] = {
                "name": day["name"],
                "topic": day["topic"],
                "group": day["group"],
                "market": day["market"],
            }

        _attach_turnover_for_date(day_rows, hist)
        for day in day_rows:
            hist[day["code"]].append(day)

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
            by_date_stocks[row["date"]].append(_stock_row(row))

    latest_date = dates[-1]
    latest_stocks = by_date_stocks.get(latest_date) or []
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
            "curated_dir": str(curated),
            "price_hits": price_hits,
            "price_miss": price_miss,
            "unit_foreign_flow": "億元",
            "unit_shares": "股",
            "unit_amount": "億元",
            "unit_curated_foreign_net": "千張 (1千張=1e6股)",
            "conversion": "foreign_flow_yi = foreign_net * price / 100  (= shares*price/1e8)",
            "etf_note": "etf_flow_yi = sum(share_delta*price/1e8) across active ETFs under data/etf/*",
            "active_etfs_used": active_etfs,
            "etf_flow_nonzero_stock_days": etf_flow_nonzero_days,
            "etf_stats": etf_stats,
            "modes": ["foreign", "etf", "combined", "turnover"],
            "turnover_fields": [
                "amount",
                "average5",
                "change_pct",
                "turnover_change",
                "market_share",
                "daily_ret",
                "cumulative_return",
            ],
            "contract": "docs/FUNDFLO_CONTRACT.md",
        },
        "stocks": latest_stocks,
        "series": series,
    }
    return latest, dates


def _stock_row(row: dict) -> dict:
    return {
        "code": row["code"],
        "name": row.get("name"),
        "foreign_flow_yi": row.get("foreign_flow_yi"),
        "etf_flow_yi": row.get("etf_flow_yi", 0.0),
        "combined_flow_yi": row.get("combined_flow_yi"),
        "rolling_foreign_5d_yi": row.get("rolling_foreign_5d_yi"),
        "momentum_foreign_5d_yi": row.get("momentum_foreign_5d_yi"),
        "rolling_etf_5d_yi": row.get("rolling_etf_5d_yi"),
        "momentum_etf_5d_yi": row.get("momentum_etf_5d_yi"),
        "rolling_combined_5d_yi": row.get("rolling_combined_5d_yi"),
        "momentum_combined_5d_yi": row.get("momentum_combined_5d_yi"),
        "rolling_ret_5d": row.get("rolling_ret_5d"),
        "shares": row.get("shares"),
        "close": row.get("close"),
        "amount": row.get("amount"),
        "average5": row.get("average5"),
        "change_pct": row.get("change_pct"),
        "turnover_change": row.get("turnover_change", row.get("change_pct")),
        "market_share": row.get("market_share"),
        "daily_ret": row.get("daily_ret", row.get("change")),
        "cumulative_return": row.get("cumulative_return", row.get("rolling_ret_5d")),
        "topic": row.get("topic"),
        "group": row.get("group"),
        "market": row.get("market"),
    }


def _score_keys(row: dict) -> List[float]:
    vals = []
    for k in (
        "rolling_foreign_5d_yi",
        "rolling_etf_5d_yi",
        "rolling_combined_5d_yi",
        "foreign_flow_yi",
        "etf_flow_yi",
        "amount",
    ):
        v = row.get(k)
        if v is not None:
            try:
                vals.append(abs(float(v)))
            except (TypeError, ValueError):
                pass
    return vals


def _compact_series(series: List[dict], keep_dates: int = 36, top_n: int = 50) -> List[dict]:
    """Keep last keep_dates days; include codes that ranked top_n on any mode metric."""
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
                scores = _score_keys(row)
                if not scores:
                    continue
                scored.append((max(scores), s["code"]))
        scored.sort(reverse=True)
        for _, code in scored[:top_n]:
            hot.add(code)
        # also ensure top amount / |etf| separately
        for key in ("amount", "etf_flow_yi", "rolling_etf_5d_yi"):
            keyed = []
            for s in series:
                for row in s.get("days") or []:
                    if row.get("date") != dt:
                        continue
                    v = row.get(key)
                    if v is None:
                        continue
                    keyed.append((abs(float(v)), s["code"]))
            keyed.sort(reverse=True)
            for _, code in keyed[: max(10, top_n // 2)]:
                hot.add(code)
    out = []
    for s in series:
        if s["code"] not in hot:
            continue
        by_dt = {d["date"]: d for d in (s.get("days") or []) if d.get("date") in keep}
        keep_list = all_dates[-keep_dates:]
        # Exact coverage so every series shares the same date axis / frameMax
        if any(dt not in by_dt for dt in keep_list):
            continue
        ordered = [by_dt[dt] for dt in keep_list]
        out.append({**s, "days": ordered})
    return out


def write_outputs(latest: dict, dates: List[str], write_by_date: bool = True) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    BY_DATE.mkdir(parents=True, exist_ok=True)

    lite = {k: v for k, v in latest.items() if k != "series"}
    (OUT_DIR / "latest.json").write_text(
        json.dumps(lite, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )
    series_top = _compact_series(latest.get("series") or [], keep_dates=36, top_n=50)
    (OUT_DIR / "series_top.json").write_text(
        json.dumps(
            {
                "meta": {
                    **latest["meta"],
                    "series_mode": "top",
                    "keep_dates": 36,
                    "top_n": 50,
                    "n_series_top": len(series_top),
                },
                "series": series_top,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
        encoding="utf-8",
    )

    if latest["meta"].get("synthetic"):
        (OUT_DIR / "fixture.json").write_text(
            json.dumps(latest, ensure_ascii=False, indent=2), encoding="utf-8"
        )
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
        by_date: Dict[str, List[dict]] = defaultdict(list)
        for s in latest.get("series") or []:
            for row in s.get("days") or []:
                by_date[row["date"]].append(_stock_row({**row, "name": row.get("name") or s.get("name")}))
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

    fix = build_synthetic_fixture()
    (OUT_DIR / "fixture.json").write_text(
        json.dumps(fix, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main() -> None:
    global CURATED_DIR
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw-dir", default=None, help="TWSE raw day dumps (MI_INDEX)")
    ap.add_argument("--curated-dir", default=None, help="Override curated JSON directory")
    ap.add_argument("--fixture-only", action="store_true")
    ap.add_argument("--max-dates", type=int, default=None)
    ap.add_argument("--skip-by-date", action="store_true")
    args = ap.parse_args()

    if args.curated_dir:
        CURATED_DIR = discover_curated_dir(args.curated_dir)

    if args.fixture_only:
        latest = build_synthetic_fixture()
        write_outputs(latest, latest["meta"]["dates"])
        print(f"wrote synthetic fixture → {OUT_DIR}")
        return

    raw = discover_raw_dir(args.raw_dir)
    print(f"curated={CURATED_DIR} raw={raw}")
    latest, dates = build(raw, max_dates=args.max_dates, curated_dir=CURATED_DIR)
    write_outputs(latest, dates, write_by_date=not args.skip_by_date)
    m = latest["meta"]
    print(
        f"date={m.get('date')} stocks={m.get('n_stocks')} series={m.get('n_series')} "
        f"price_hits={m.get('price_hits')} price_miss={m.get('price_miss')} "
        f"active_etfs={m.get('active_etfs_used')} etf_nz={m.get('etf_flow_nonzero_stock_days')} → {OUT_DIR}"
    )


if __name__ == "__main__":
    main()
