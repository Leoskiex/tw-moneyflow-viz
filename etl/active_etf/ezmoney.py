"""統一投信 ezMoney DataAsset holdings (00981A etc.)."""
from __future__ import annotations

import html as html_lib
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from . import common


def fetch_html(fund_code: str) -> str:
    url = f"https://www.ezmoney.com.tw/ETF/Fund/Info?FundCode={fund_code}"
    raw = common.curl_bytes(url, cookie_jar=True, headers={"Accept": "text/html,*/*"})
    return raw.decode("utf-8", errors="replace")


def parse_data_asset(html: str) -> list:
    m = re.search(r'<div id="DataAsset" data-content="([^"]*)"', html)
    if not m:
        raise ValueError("DataAsset div not found on ezMoney Info page")
    data = json.loads(html_lib.unescape(m.group(1)))
    if not isinstance(data, list):
        raise ValueError("DataAsset is not a list")
    return data


def extract_stock_holdings(assets: list) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
    st = next((a for a in assets if a.get("AssetCode") == "ST"), None)
    if not st:
        raise ValueError("AssetCode ST (股票) missing")
    details = st.get("Details") or []
    if not details:
        raise ValueError("ST Details empty")
    tran = str(details[0].get("TranDate") or "")[:10]
    date = common.norm_date(tran)
    holdings: List[Dict[str, Any]] = []
    for d in details:
        code = str(d.get("DetailCode") or "").strip()
        if not code or not code.isdigit():
            continue
        holdings.append(
            {
                "code": code,
                "name": str(d.get("DetailName") or "").strip(),
                "share": float(d.get("Share") or 0),
                "amount": float(d.get("Amount") or 0),
                "weight_pct": float(d.get("NavRate") or 0),
                "money_type": d.get("MoneyType") or "NTD",
            }
        )
    common.sort_holdings(holdings)
    meta = {
        "asset_name": st.get("AssetName"),
        "n_raw_details": len(details),
        "n_equity": len(holdings),
        "weight_sum_equity": round(sum(h["weight_pct"] for h in holdings), 4),
    }
    return date, holdings, meta


def fetch_holdings(entry: Dict[str, Any], html: Optional[str] = None) -> Dict[str, Any]:
    fund_code = entry.get("fund_code")
    if not fund_code:
        raise ValueError(f"{entry.get('code')}: ezmoney requires fund_code")
    url = entry.get("info_url") or f"https://www.ezmoney.com.tw/ETF/Fund/Info?FundCode={fund_code}"
    if html is None:
        html = fetch_html(fund_code)
    assets = parse_data_asset(html)
    date, holdings, meta = extract_stock_holdings(assets)
    meta.update({"fund_code": fund_code, "etf_code": entry["code"]})
    path = common.save_snapshot(
        etf=entry["code"],
        date=date,
        holdings=holdings,
        meta=meta,
        source="ezmoney",
        source_url=url,
        fund_code=fund_code,
    )
    return {"date": date, "n": len(holdings), "path": str(path), "meta": meta, "source": "ezmoney"}
