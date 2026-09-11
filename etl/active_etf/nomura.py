"""野村投信 ETFWEB GetFundAssets API (日揭持股比重)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from . import common

API = "https://www.nomurafunds.com.tw/API/ETFAPI/api/Fund/GetFundAssets"


def _candidate_dates(preferred: Optional[str] = None) -> List[str]:
    out: List[str] = []
    if preferred:
        out.append(preferred)
    today = datetime.now(common.TZ8).date()
    for i in range(0, 10):
        d = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        if d not in out:
            out.append(d)
    return out


def post_assets(fund_id: str, search_date: str) -> dict:
    body = json.dumps({"FundID": fund_id, "SearchDate": search_date})
    return common.curl_json(
        API,
        method="POST",
        body=body,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": "https://www.nomurafunds.com.tw",
            "Referer": "https://www.nomurafunds.com.tw/ETFWEB/",
        },
    )


def parse_stock_table(payload: dict) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
    if payload.get("StatusCode") not in (0, "0", None) and not (
        ((payload.get("Entries") or {}).get("Data") or {}).get("Table")
    ):
        raise ValueError(f"Nomura StatusCode={payload.get('StatusCode')} Message={payload.get('Message')}")
    data = ((payload.get("Entries") or {}).get("Data") or {})
    tables = data.get("Table") or []
    stock = next((t for t in tables if (t.get("TableTitle") or "") == "股票"), None)
    if not stock or not (stock.get("Rows") or []):
        raise ValueError("Nomura 股票 table empty")
    nav_date = common.norm_date(str(stock.get("NavDate") or ""))
    aum = None
    fa = data.get("FundAsset") or {}
    try:
        aum = float(str(fa.get("Aum") or "").replace(",", "")) if fa.get("Aum") not in (None, "") else None
    except ValueError:
        aum = None
    holdings: List[Dict[str, Any]] = []
    for row in stock.get("Rows") or []:
        if not row or len(row) < 4:
            continue
        code = str(row[0]).strip()
        if not common.equity_only(code) and not (code.isdigit() and len(code) >= 4):
            # keep 4-digit TW equities; skip futures codes etc.
            if not (code.isdigit() and 4 <= len(code) <= 6):
                continue
        name = str(row[1]).strip()
        share = float(str(row[2]).replace(",", "") or 0)
        weight = float(str(row[3]).replace(",", "") or 0)
        amount = round(aum * weight / 100.0, 2) if aum is not None else 0.0
        holdings.append(
            {
                "code": code,
                "name": name,
                "share": share,
                "amount": amount,
                "weight_pct": weight,
                "money_type": "NTD",
            }
        )
    if not holdings:
        raise ValueError("Nomura equity holdings empty after filter")
    common.sort_holdings(holdings)
    meta = {
        "etf_code": None,
        "nav_date": nav_date,
        "aum": aum,
        "nav": fa.get("Nav"),
        "units": fa.get("Units"),
        "n_equity": len(holdings),
        "weight_sum_equity": round(sum(h["weight_pct"] for h in holdings), 4),
        "amount_estimated_from_aum_weight": aum is not None,
    }
    return nav_date, holdings, meta


def fetch_holdings(entry: Dict[str, Any], search_date: Optional[str] = None) -> Dict[str, Any]:
    code = entry["code"]
    last_err: Optional[Exception] = None
    payload = None
    used = None
    for d in _candidate_dates(search_date):
        try:
            payload = post_assets(code, d)
            tables = ((payload.get("Entries") or {}).get("Data") or {}).get("Table") or []
            if tables:
                used = d
                break
        except Exception as e:  # noqa: BLE001
            last_err = e
            continue
    if not payload or not used:
        raise RuntimeError(f"Nomura GetFundAssets no data for {code}: {last_err}")
    date, holdings, meta = parse_stock_table(payload)
    meta["etf_code"] = code
    meta["search_date_tried"] = used
    url = entry.get("info_url") or API
    path = common.save_snapshot(
        etf=code,
        date=date,
        holdings=holdings,
        meta=meta,
        source="nomura_api",
        source_url=url,
        fund_code=None,
    )
    return {"date": date, "n": len(holdings), "path": str(path), "meta": meta, "source": "nomura_api"}
