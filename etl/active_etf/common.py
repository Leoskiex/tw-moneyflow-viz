"""Shared holdings snapshot schema + IO (aligned with fetch_00981a)."""
from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

TZ8 = timezone(timedelta(hours=8))
UA = "Mozilla/5.0 (compatible; tw-moneyflow/1.0; +local)"
VIZ_ROOT = Path(os.environ.get("TW_VIZ_ROOT", "/workspace/tw-moneyflow-viz"))


def now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def curl_bytes(url: str, *, timeout: int = 45, headers: Optional[Dict[str, str]] = None,
               method: str = "GET", body: Optional[str] = None, cookie_jar: bool = False) -> bytes:
    args = ["curl", "-skL", "--max-time", str(timeout), "--max-redirs", "10", "-A", UA]
    if headers:
        for k, v in headers.items():
            args += ["-H", f"{k}: {v}"]
    ck = None
    if cookie_jar:
        f = tempfile.NamedTemporaryFile(prefix="etfck_", suffix=".ck", delete=False)
        f.close()
        ck = f.name
        args += ["-c", ck, "-b", ck]
    if method.upper() == "POST":
        args += ["-X", "POST"]
        if body is not None:
            args += ["-d", body]
    args.append(url)
    try:
        r = subprocess.run(args, capture_output=True, check=False)
        if r.returncode != 0 or not r.stdout:
            err = (r.stderr or b"")[:300]
            raise RuntimeError(f"curl failed rc={r.returncode} url={url} err={err!r}")
        return r.stdout
    finally:
        if ck:
            Path(ck).unlink(missing_ok=True)


def curl_json(url: str, **kwargs: Any) -> Any:
    raw = curl_bytes(url, **kwargs)
    return json.loads(raw.decode("utf-8", errors="replace"))


def norm_date(s: str) -> str:
    s = (s or "").strip()
    if not s:
        raise ValueError("empty date")
    # 2026-09-10T00:00:00 / 2026/09/10 / 2026/9/11 上午 ...
    s = s.replace("上午", " ").replace("下午", " ")
    m = re.match(r"(\d{4})[/-](\d{1,2})[/-](\d{1,2})", s)
    if not m:
        raise ValueError(f"bad date: {s!r}")
    return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"


def holdings_dirs(code: str) -> tuple[Path, Path]:
    low = code.strip().lower()
    base = VIZ_ROOT / "data" / "etf" / low
    return base / "holdings", base / "holdings_latest.json"


def save_snapshot(
    *,
    etf: str,
    date: str,
    holdings: List[Dict[str, Any]],
    meta: Dict[str, Any],
    source: str,
    source_url: str,
    fund_code: Optional[str] = None,
) -> Path:
    out_dir, out_latest = holdings_dirs(etf)
    out_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "date": date,
        "etf": etf.upper(),
        "fund_code": fund_code,
        "source": source,
        "source_url": source_url,
        "fetched_at": now_iso(),
        "meta": meta,
        "holdings": holdings,
    }
    path = out_dir / f"{date}.json"
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    path.write_text(text, encoding="utf-8")
    out_latest.write_text(text, encoding="utf-8")
    return path


def equity_only(code: str) -> bool:
    """Keep TW listed equity codes (4–6 digits, optional trailing letter rare)."""
    c = (code or "").strip()
    return bool(re.match(r"^\d{4}(\d{0,2})?[A-Z]?$", c)) and not c.startswith("00")


def sort_holdings(holdings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    holdings.sort(key=lambda x: (-float(x.get("weight_pct") or 0), str(x.get("code") or "")))
    return holdings
