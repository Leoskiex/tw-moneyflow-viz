"""Priority TW active equity ETF registry (sixth char often A).

AISTOCKMAP path: data/etf/<lowercase_code>/holdings/YYYY-MM-DD.json
+ holdings_latest.json

瑤池金母（陳釧瑤）主線：00981A（統一／ezMoney 49YTW）。
同投信可日揭姊妹檔：00403A／00988A／00411A（非瑤池主線，僅補強 etf_flow_yi）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

# cadence: daily = 日揭持股；monthly = 官網表偏月更／待確認；stub = 尚未接通
REGISTRY: List[Dict[str, Any]] = [
    {
        "code": "00981A",
        "name": "主動統一台股增長",
        "issuer": "統一投信",
        "manager_note": "瑤池金母／陳釧瑤 — 成長主題雷達主線",
        "source_kind": "ezmoney",
        "fund_code": "49YTW",
        "info_url": "https://www.ezmoney.com.tw/ETF/Fund/Info?FundCode=49YTW",
        "api_url": None,
        "holdings_path": "data/etf/00981a/holdings",
        "cadence": "daily",
        "priority": 1,
        "enabled": True,
    },
    {
        "code": "00403A",
        "name": "主動統一升級50",
        "issuer": "統一投信",
        "manager_note": "統一姊妹檔（瑤姐相關全包優先序）",
        "source_kind": "ezmoney",
        "fund_code": "63YTW",
        "info_url": "https://www.ezmoney.com.tw/ETF/Fund/Info?FundCode=63YTW",
        "api_url": None,
        "holdings_path": "data/etf/00403a/holdings",
        "cadence": "daily",
        "priority": 2,
        "enabled": True,
    },
    {
        "code": "00980A",
        "name": "主動野村臺灣優選",
        "issuer": "野村投信",
        "source_kind": "nomura_api",
        "fund_code": None,
        "info_url": "https://www.nomurafunds.com.tw/ETFWEB/product-description?fundNo=00980A&tab=Shareholding",
        "api_url": "https://www.nomurafunds.com.tw/API/ETFAPI/api/Fund/GetFundAssets",
        "holdings_path": "data/etf/00980a/holdings",
        "cadence": "daily",
        "priority": 3,
        "enabled": True,
    },
    {
        "code": "00982A",
        "name": "主動群益台灣強棒",
        "issuer": "群益投信",
        "source_kind": "capital_api",
        "fund_code": None,
        "product_id": 399,
        "info_url": "https://www.capitalfund.com.tw/etf/product/detail/399/portfolio",
        "api_url": "https://www.capitalfund.com.tw/CFWeb/api/etf/buyback",
        "holdings_path": "data/etf/00982a/holdings",
        "cadence": "daily",
        "priority": 4,
        "enabled": True,
    },
    {
        "code": "00985A",
        "name": "主動野村台灣50",
        "issuer": "野村投信",
        "source_kind": "nomura_api",
        "fund_code": None,
        "info_url": "https://www.nomurafunds.com.tw/ETFWEB/product-description?fundNo=00985A&tab=Shareholding",
        "api_url": "https://www.nomurafunds.com.tw/API/ETFAPI/api/Fund/GetFundAssets",
        "holdings_path": "data/etf/00985a/holdings",
        "cadence": "daily",
        "priority": 5,
        "enabled": True,
    },
    {
        "code": "00987A",
        "name": "主動台新優勢成長",
        "issuer": "台新投信",
        "source_kind": "taishin_html",
        "fund_code": None,
        "info_url": "https://www.tsit.com.tw/ETF/Home/ETFSeriesDetail/00987A",
        "api_url": None,
        "holdings_path": "data/etf/00987a/holdings",
        "cadence": "daily",  # HTML SSR 有完整持股；基準日欄位不明時用抓取日並記 meta
        "priority": 6,
        "enabled": True,
        "todo": "確認官網持股基準日欄位；若僅月更改 cadence=monthly",
    },
    {
        "code": "00992A",
        "name": "主動群益科技創新",
        "issuer": "群益投信",
        "source_kind": "capital_api",
        "fund_code": None,
        "product_id": 500,
        "info_url": "https://www.capitalfund.com.tw/etf/product/detail/500/portfolio",
        "api_url": "https://www.capitalfund.com.tw/CFWeb/api/etf/buyback",
        "holdings_path": "data/etf/00992a/holdings",
        "cadence": "daily",
        "priority": 7,
        "enabled": True,
    },
    {
        "code": "00999A",
        "name": "主動野村臺灣高息",
        "issuer": "野村投信",
        "source_kind": "nomura_api",
        "fund_code": None,
        "info_url": "https://www.nomurafunds.com.tw/ETFWEB/product-description?fundNo=00999A&tab=Shareholding",
        "api_url": "https://www.nomurafunds.com.tw/API/ETFAPI/api/Fund/GetFundAssets",
        "holdings_path": "data/etf/00999a/holdings",
        "cadence": "daily",
        "priority": 8,
        "enabled": True,
    },
    {
        "code": "00988A",
        "name": "主動統一全球創新",
        "issuer": "統一投信",
        "manager_note": "瑤姐相關統一姊妹檔（全球股；ST 可能含海外代碼，僅計台股數字碼）",
        "source_kind": "ezmoney",
        "fund_code": "61YTW",
        "info_url": "https://www.ezmoney.com.tw/ETF/Fund/Info?FundCode=61YTW",
        "api_url": None,
        "holdings_path": "data/etf/00988a/holdings",
        "cadence": "daily",
        "priority": 9,
        "enabled": True,
    },
    {
        "code": "00411A",
        "name": "主動統一前沿科技",
        "issuer": "統一投信",
        "manager_note": "瑤姐相關統一姊妹檔",
        "source_kind": "ezmoney",
        "fund_code": "64YTW",
        "info_url": "https://www.ezmoney.com.tw/ETF/Fund/Info?FundCode=64YTW",
        "api_url": None,
        "holdings_path": "data/etf/00411a/holdings",
        "cadence": "daily",
        "priority": 10,
        "enabled": True,
    },
]


def get_registry(*, enabled_only: bool = False) -> List[Dict[str, Any]]:
    rows = sorted(REGISTRY, key=lambda r: (r.get("priority", 99), r["code"]))
    if enabled_only:
        rows = [r for r in rows if r.get("enabled", True)]
    return rows


def by_code(code: str) -> Optional[Dict[str, Any]]:
    c = code.strip().upper()
    for r in REGISTRY:
        if r["code"].upper() == c:
            return r
    return None
