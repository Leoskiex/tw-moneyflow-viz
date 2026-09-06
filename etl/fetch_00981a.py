#!/usr/bin/env python3
"""Fetch 00981A (ezMoney FundCode 49YTW) daily stock holdings.

Source of truth: https://www.ezmoney.com.tw/ETF/Fund/Info?FundCode=49YTW
Holdings live in <div id="DataAsset" data-content="..."> (HTML-escaped JSON).
AssetCode == "ST" → Details[] with DetailCode / DetailName / Share / NavRate / TranDate.

Saves:
  /workspace/tw-moneyflow-viz/data/etf/00981a/holdings/<YYYY-MM-DD>.json
  /workspace/tw-moneyflow-viz/data/etf/00981a/holdings_latest.json
"""
from __future__ import annotations

import html as html_lib
import json
import re
import ssl
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

FUND_CODE = "49YTW"
ETF_CODE = "00981A"
INFO_URL = f"https://www.ezmoney.com.tw/ETF/Fund/Info?FundCode={FUND_CODE}"
OUT_DIR = Path("/workspace/tw-moneyflow-viz/data/etf/00981a/holdings")
OUT_LATEST = Path("/workspace/tw-moneyflow-viz/data/etf/00981a/holdings_latest.json")
UA = "Mozilla/5.0 (compatible; tw-moneyflow/1.0; +local)"

TZ8 = timezone(timedelta(hours=8))


def _now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def _fetch(url: str, timeout: int = 45) -> bytes:
    """ezMoney redirects need a cookie jar; bare curl -L can loop."""
    import subprocess
    import tempfile
    ck = tempfile.NamedTemporaryFile(prefix="ez981_", suffix=".ck", delete=False)
    ck.close()
    try:
        r = subprocess.run(
            [
                "curl", "-skL", "--max-time", str(timeout),
                "--max-redirs", "10",
                "-A", UA,
                "-H", "Accept: text/html,*/*",
                "-c", ck.name, "-b", ck.name,
                url,
            ],
            capture_output=True,
            check=False,
        )
        if r.returncode != 0 or not r.stdout:
            raise RuntimeError(f"curl failed rc={r.returncode} err={r.stderr[:200]!r}")
        return r.stdout
    finally:
        Path(ck.name).unlink(missing_ok=True)


def parse_data_asset(html: str) -> list[dict[str, Any]]:
    m = re.search(r'<div id="DataAsset" data-content="([^"]*)"', html)
    if not m:
        raise ValueError("DataAsset div not found on ezMoney Info page")
    decoded = html_lib.unescape(m.group(1))
    data = json.loads(decoded)
    if not isinstance(data, list):
        raise ValueError("DataAsset is not a list")
    return data


def extract_stock_holdings(assets: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    st = next((a for a in assets if a.get("AssetCode") == "ST"), None)
    if not st:
        raise ValueError("AssetCode ST (股票) missing")
    details = st.get("Details") or []
    if not details:
        raise ValueError("ST Details empty")
    tran = str(details[0].get("TranDate") or "")[:10]
    if not re.match(r"\d{4}-\d{2}-\d{2}", tran):
        raise ValueError(f"bad TranDate: {tran!r}")

    holdings: list[dict[str, Any]] = []
    for d in details:
        code = str(d.get("DetailCode") or "").strip()
        if not code or not code.isdigit():
            continue  # skip futures / non-equity
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
    holdings.sort(key=lambda x: (-x["weight_pct"], x["code"]))

    meta = {
        "fund_code": FUND_CODE,
        "etf_code": ETF_CODE,
        "asset_name": st.get("AssetName"),
        "n_raw_details": len(details),
        "n_equity": len(holdings),
        "weight_sum_equity": round(sum(h["weight_pct"] for h in holdings), 4),
    }
    return tran, holdings, meta


def save_snapshot(date: str, holdings: list[dict[str, Any]], meta: dict[str, Any], source_url: str) -> Path:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "date": date,
        "etf": ETF_CODE,
        "fund_code": FUND_CODE,
        "source": "ezmoney",
        "source_url": source_url,
        "fetched_at": _now_iso(),
        "meta": meta,
        "holdings": holdings,
    }
    path = OUT_DIR / f"{date}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_LATEST.parent.mkdir(parents=True, exist_ok=True)
    OUT_LATEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def fetch_and_save(html: Optional[str] = None) -> dict[str, Any]:
    if html is None:
        raw = _fetch(INFO_URL)
        html = raw.decode("utf-8", errors="replace")
    assets = parse_data_asset(html)
    date, holdings, meta = extract_stock_holdings(assets)
    path = save_snapshot(date, holdings, meta, INFO_URL)
    return {"date": date, "n": len(holdings), "path": str(path), "meta": meta}


def list_saved_dates() -> list[str]:
    if not OUT_DIR.exists():
        return []
    return sorted(p.stem for p in OUT_DIR.glob("*.json") if re.match(r"\d{4}-\d{2}-\d{2}", p.stem))


def load_holdings(date: Optional[str] = None) -> Optional[dict[str, Any]]:
    if date:
        p = OUT_DIR / f"{date}.json"
        if not p.exists():
            return None
        return json.loads(p.read_text(encoding="utf-8"))
    if OUT_LATEST.exists():
        return json.loads(OUT_LATEST.read_text(encoding="utf-8"))
    dates = list_saved_dates()
    if not dates:
        return None
    return json.loads((OUT_DIR / f"{dates[-1]}.json").read_text(encoding="utf-8"))


def main() -> None:
    result = fetch_and_save()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    top = load_holdings(result["date"])
    assert top
    print("top5:", [(h["code"], h["name"], h["weight_pct"]) for h in top["holdings"][:5]])


if __name__ == "__main__":
    main()
