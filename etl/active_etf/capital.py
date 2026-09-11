"""群益投信 CFWeb /api/etf/buyback PCF stocks (日揭)."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from . import common

API = "https://www.capitalfund.com.tw/CFWeb/api/etf/buyback"


def post_buyback(product_id: int) -> dict:
    body = json.dumps({"fundId": int(product_id)})
    return common.curl_json(
        API,
        method="POST",
        body=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": "https://www.capitalfund.com.tw",
            "Referer": "https://www.capitalfund.com.tw/etf/product/",
        },
    )


def parse_stocks(payload: dict) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
    if payload.get("code") not in (200, "200", None) and "data" not in payload:
        raise ValueError(f"Capital buyback code={payload.get('code')} msg={payload.get('message')}")
    data = payload.get("data") or {}
    stocks = data.get("stocks") or []
    if not stocks:
        raise ValueError("Capital stocks empty")
    pcf = data.get("pcf") or {}
    # Prefer stock row date1; fallback pcf.date1 / date2
    date_raw = str(stocks[0].get("date1") or pcf.get("date1") or pcf.get("date2") or "")
    date = common.norm_date(date_raw)
    aum = None
    try:
        if pcf.get("nav") is not None:
            aum = float(pcf["nav"])
    except (TypeError, ValueError):
        aum = None
    holdings: List[Dict[str, Any]] = []
    for s in stocks:
        code = str(s.get("stocNo") or "").strip()
        if not code or not re.match(r"^\d{4}", code):
            continue
        # strip TPEx * suffix in names already separate
        share = float(s.get("share") or 0)
        weight = float(s.get("weight") if s.get("weight") is not None else (s.get("weightRound") or 0))
        amount = round(aum * weight / 100.0, 2) if aum is not None else 0.0
        holdings.append(
            {
                "code": code,
                "name": str(s.get("stocName") or "").strip(),
                "share": share,
                "amount": amount,
                "weight_pct": round(weight, 4),
                "money_type": "NTD",
            }
        )
    if not holdings:
        raise ValueError("Capital equity holdings empty")
    common.sort_holdings(holdings)
    meta = {
        "product_id": None,
        "pcf_date1": pcf.get("date1"),
        "pcf_date2": pcf.get("date2"),
        "aum": aum,
        "tot_unit": pcf.get("totUnit"),
        "n_equity": len(holdings),
        "weight_sum_equity": round(sum(h["weight_pct"] for h in holdings), 4),
        "amount_estimated_from_nav_weight": aum is not None,
        "fund_name": pcf.get("fundName"),
    }
    return date, holdings, meta


def fetch_holdings(entry: Dict[str, Any]) -> Dict[str, Any]:
    pid = entry.get("product_id")
    if pid is None:
        raise ValueError(f"{entry.get('code')}: capital_api requires product_id")
    payload = post_buyback(int(pid))
    date, holdings, meta = parse_stocks(payload)
    meta["product_id"] = int(pid)
    meta["etf_code"] = entry["code"]
    url = entry.get("info_url") or API
    path = common.save_snapshot(
        etf=entry["code"],
        date=date,
        holdings=holdings,
        meta=meta,
        source="capital_api",
        source_url=url,
        fund_code=None,
    )
    return {"date": date, "n": len(holdings), "path": str(path), "meta": meta, "source": "capital_api"}
