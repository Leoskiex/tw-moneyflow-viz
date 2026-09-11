"""台新投信 ETFSeriesDetail HTML holdings (SSR table).

TODO: confirm official as-of date field on page; if only month-end, set cadence=monthly.
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from . import common


def fetch_html(code: str) -> str:
    url = f"https://www.tsit.com.tw/ETF/Home/ETFSeriesDetail/{code}"
    raw = common.curl_bytes(url, headers={"Accept": "text/html,*/*"})
    return raw.decode("utf-8", errors="replace")


def parse_holdings_table(html: str) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
    rows = re.findall(
        r"<td>\s*(\d{4,6})\s*TT\s*</td>\s*<td>\s*([^<]+?)\s*</td>\s*<td>\s*([\d,]+)\s*</td>\s*<td>\s*([\d.]+)\s*%?\s*</td>",
        html,
        flags=re.I,
    )
    if not rows:
        raise ValueError("Taishin holdings table not found / empty")
    # Prefer recent as-of dates on page; skip listing/成立 dates (2025-12-*).
    candidates = []
    for m in re.finditer(r"(20\d{2})[/-](\d{1,2})[/-](\d{1,2})", html):
        try:
            d = common.norm_date(m.group(0))
        except ValueError:
            continue
        if d.startswith("2025-12"):
            continue  # 成立/上市日
        candidates.append(d)
    date = None
    date_source = "fetch_day_fallback"
    if candidates:
        # pick max date that is not far-future; prefer 2026/9/10 style near NAV
        date = max(candidates)
        date_source = "page_max_non_listing"
    if not date:
        date = datetime.now(common.TZ8).date().isoformat()
    holdings: List[Dict[str, Any]] = []
    for code, name, share_s, w_s in rows:
        code = code.strip()
        if not re.match(r"^\d{4}", code):
            continue
        share = float(share_s.replace(",", ""))
        weight = float(w_s)
        holdings.append(
            {
                "code": code,
                "name": name.strip(),
                "share": share,
                "amount": 0.0,  # page has no amount; leave 0 rather than invent
                "weight_pct": weight,
                "money_type": "NTD",
            }
        )
    common.sort_holdings(holdings)
    meta = {
        "n_equity": len(holdings),
        "weight_sum_equity": round(sum(h["weight_pct"] for h in holdings), 4),
        "date_source": date_source,
        "todo": "confirm holdings as-of date on issuer page",
        "amount_missing": True,
    }
    return date, holdings, meta


def fetch_holdings(entry: Dict[str, Any], html: Optional[str] = None) -> Dict[str, Any]:
    code = entry["code"]
    url = entry.get("info_url") or f"https://www.tsit.com.tw/ETF/Home/ETFSeriesDetail/{code}"
    if html is None:
        html = fetch_html(code)
    date, holdings, meta = parse_holdings_table(html)
    meta["etf_code"] = code
    path = common.save_snapshot(
        etf=code,
        date=date,
        holdings=holdings,
        meta=meta,
        source="taishin_html",
        source_url=url,
        fund_code=None,
    )
    return {"date": date, "n": len(holdings), "path": str(path), "meta": meta, "source": "taishin_html"}
