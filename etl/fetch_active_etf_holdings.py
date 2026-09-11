#!/usr/bin/env python3
"""Batch-fetch Taiwan active equity ETF holdings into AISTOCKMAP paths.

Writes:
  {TW_VIZ_ROOT}/data/etf/<code>/holdings/YYYY-MM-DD.json
  {TW_VIZ_ROOT}/data/etf/<code>/holdings_latest.json

Usage:
  python3 fetch_active_etf_holdings.py
  python3 fetch_active_etf_holdings.py --codes 00980A,00982A
  python3 fetch_active_etf_holdings.py --list
"""
from __future__ import annotations

import argparse
import json
import sys
import traceback
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from active_etf.registry import get_registry, by_code  # noqa: E402
from active_etf import ezmoney, nomura, capital, taishin  # noqa: E402


def dispatch(entry: Dict[str, Any]) -> Dict[str, Any]:
    kind = entry.get("source_kind")
    if kind == "ezmoney":
        return ezmoney.fetch_holdings(entry)
    if kind == "nomura_api":
        return nomura.fetch_holdings(entry)
    if kind == "capital_api":
        return capital.fetch_holdings(entry)
    if kind == "taishin_html":
        return taishin.fetch_holdings(entry)
    raise ValueError(f"unsupported source_kind={kind!r} for {entry.get('code')}")


def run_batch(codes: List[str] | None = None, *, enabled_only: bool = True) -> Dict[str, Any]:
    if codes:
        entries = []
        for c in codes:
            e = by_code(c)
            if not e:
                entries.append({"code": c.upper(), "_missing": True})
            else:
                entries.append(e)
    else:
        entries = get_registry(enabled_only=enabled_only)

    ok: List[Dict[str, Any]] = []
    fail: List[Dict[str, Any]] = []
    for entry in entries:
        code = entry.get("code", "?")
        if entry.get("_missing"):
            fail.append({"code": code, "error": "not in registry"})
            print(f"FAIL {code}: not in registry", flush=True)
            continue
        if codes is None and not entry.get("enabled", True):
            continue
        try:
            result = dispatch(entry)
            row = {"code": code, **result}
            ok.append(row)
            print(f"OK   {code} date={result.get('date')} n={result.get('n')} path={result.get('path')}", flush=True)
        except Exception as e:  # noqa: BLE001 — batch must not abort
            fail.append({
                "code": code,
                "error": str(e),
                "source_kind": entry.get("source_kind"),
                "info_url": entry.get("info_url") or entry.get("api_url"),
                "traceback": traceback.format_exc()[-800:],
            })
            print(f"FAIL {code}: {e}", flush=True)
    return {"ok": ok, "fail": fail, "n_ok": len(ok), "n_fail": len(fail)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Fetch TW active ETF holdings (batch, non-blocking failures)")
    ap.add_argument("--codes", help="Comma-separated ETF codes (default: all enabled registry)")
    ap.add_argument("--all", action="store_true", help="Include disabled registry rows")
    ap.add_argument("--list", action="store_true", help="Print registry and exit")
    ap.add_argument("--json-out", help="Write summary JSON path")
    args = ap.parse_args()

    if args.list:
        rows = get_registry(enabled_only=False)
        print(json.dumps(rows, ensure_ascii=False, indent=2))
        return 0

    codes = [c.strip() for c in args.codes.split(",") if c.strip()] if args.codes else None
    summary = run_batch(codes, enabled_only=not args.all)
    print(json.dumps({"n_ok": summary["n_ok"], "n_fail": summary["n_fail"],
                      "ok_codes": [x["code"] for x in summary["ok"]],
                      "fail_codes": [x["code"] for x in summary["fail"]]},
                     ensure_ascii=False, indent=2))
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    # non-zero only if nothing succeeded when something was requested
    if summary["n_ok"] == 0 and (codes or True):
        return 2 if summary["n_fail"] else 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
