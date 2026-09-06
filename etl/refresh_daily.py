#!/usr/bin/env python3
"""Daily incremental refresh for TW money-flow pipeline.

Schedule target (Asia/Taipei, weekdays):
  - 18:30  primary (T86 不含鉅額 ~18:00)
  - 20:45  optional second pass (含鉅額 ~20:00) — same script, force=True

Steps:
  1) Fetch latest trade-day TWSE/TPEx raw (force overwrite)
  2) Shared overlays: gap4, rules, qfiis for that day
  3) build_curated → regimes → screens → 00981A
  4) Write status JSON for LaunchAgent / digest

Paths default to /workspace; override with TWSE_ROOT / TW_VIZ_ROOT.
"""
from __future__ import annotations

import json
import os
import sys
import traceback
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

TZ = timezone(timedelta(hours=8))
ROOT = Path(os.environ.get("TWSE_ROOT", "/workspace/twse-trading"))
VIZ = Path(os.environ.get("TW_VIZ_ROOT", "/workspace/tw-moneyflow-viz"))
STATUS_PATH = VIZ / "data" / "refresh_status.json"

# Ensure imports resolve
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)


def now_iso() -> str:
    return datetime.now(TZ).isoformat(timespec="seconds")


def load_holidays() -> set[date]:
    import backfill_60 as bf
    return bf.load_holidays()


def latest_trade_day(as_of: date | None = None) -> date:
    """Most recent TW trading day on or before as_of (Taipei)."""
    holidays = load_holidays()
    d = as_of or datetime.now(TZ).date()
    # Before 15:00, yesterday's session is still the "latest complete" target
    # for morning runs; after 15:00 allow today if weekday.
    now = datetime.now(TZ)
    if as_of is None and now.hour < 15:
        d = d - timedelta(days=1)
    while d.weekday() >= 5 or d in holidays:
        d -= timedelta(days=1)
    return d


def fetch_day_force(trade: date) -> dict:
    import backfill_60 as bf

    ymd = trade.strftime("%Y%m%d")
    folder = trade.strftime("%Y-%m-%d")
    day_dir = bf.RAW / folder
    day_dir.mkdir(parents=True, exist_ok=True)

    # Temporarily disable skip-if-exists
    orig = bf.already_ok
    bf.already_ok = lambda path: False  # type: ignore
    results = {"date": folder, "ok": [], "fail": [], "nodata": []}
    try:
        for fname, url in bf.endpoints_for(ymd):
            path = day_dir / fname
            # delete so fetch always writes fresh
            if path.exists():
                path.unlink()
            st, detail = bf.fetch_and_save(url, path)
            ep = fname.replace(".json", "")
            if st == "ok":
                results["ok"].append(ep)
            elif st == "nodata":
                results["nodata"].append(ep)
            else:
                results["fail"].append({"ep": ep, "detail": detail})
                print(f"  FAIL {ep}: {detail}")
            print(f"  {st:6} {ep} {detail}")
    finally:
        bf.already_ok = orig

    # Core check
    t86 = day_dir / "T86.json"
    results["core_ok"] = t86.exists() and t86.stat().st_size > 1000
    return results


def fetch_overlays(trade: date) -> dict:
    out = {}
    folder = trade.strftime("%Y-%m-%d")
    try:
        import fetch_gap4
        fetch_gap4.main() if hasattr(fetch_gap4, "main") else None
        out["gap4"] = "ok"
    except Exception as e:
        out["gap4"] = f"err:{e}"
        print("gap4", e)
    try:
        import fetch_rules_overlay as fro
        # prefer day-specific if available
        if hasattr(fro, "main"):
            fro.main()
        out["rules"] = "ok"
    except Exception as e:
        out["rules"] = f"err:{e}"
        print("rules", e)
    try:
        import fetch_tpex_qfiis as fq
        if hasattr(fq, "fetch_day"):
            fq.fetch_day(folder)
        if hasattr(fq, "fetch_cat_once"):
            fq.fetch_cat_once()
        out["tpex_qfiis"] = "ok"
    except Exception as e:
        out["tpex_qfiis"] = f"err:{e}"
        print("tpex_qfiis", e)
    return out


def build_all() -> dict:
    out = {}
    # build_curated.main builds curated + regimes + screens + 00981a
    import build_curated
    build_curated.main()
    out["build_curated"] = "ok"
    try:
        from build_regime_brief import build as build_regime_brief
        br = build_regime_brief(all_days=False)
        out["regime_brief"] = (br.get("latest") or {}).get("date")
    except Exception as e:
        out["regime_brief"] = f"err:{e}"
    try:
        from build_daily_digest import build as build_daily_digest
        dig = build_daily_digest()
        out["digest"] = dig.get("date")
    except Exception as e:
        out["digest"] = f"err:{e}"
    # verify artifacts
    latest_screen = VIZ / "data" / "screens_latest.json"
    latest_regime = VIZ / "data" / "regime_latest.json"
    latest_981 = VIZ / "data" / "etf" / "00981a" / "latest.json"
    out["artifacts"] = {
        "screens": latest_screen.exists(),
        "regime": latest_regime.exists(),
        "etf_00981a": latest_981.exists(),
    }
    if latest_screen.exists():
        j = json.loads(latest_screen.read_text(encoding="utf-8"))
        out["screens_date"] = j.get("date")
    if latest_981.exists():
        j = json.loads(latest_981.read_text(encoding="utf-8"))
        out["etf_date"] = j.get("date")
    return out


def write_status(payload: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    started = now_iso()
    force_date = None
    if len(sys.argv) > 1 and sys.argv[1] not in ("--help", "-h"):
        force_date = date.fromisoformat(sys.argv[1])
    trade = force_date or latest_trade_day()
    print(f"refresh_daily start {started} trade_day={trade}")
    status: dict = {
        "started": started,
        "trade_day": trade.isoformat(),
        "ok": False,
        "steps": {},
    }
    try:
        status["steps"]["fetch"] = fetch_day_force(trade)
        if not status["steps"]["fetch"].get("core_ok"):
            status["error"] = "T86 core missing — official data may not be published yet"
            status["finished"] = now_iso()
            write_status(status)
            print(status["error"])
            return 2
        status["steps"]["overlays"] = fetch_overlays(trade)
        status["steps"]["build"] = build_all()
        status["ok"] = True
        status["finished"] = now_iso()
        write_status(status)
        print("refresh_daily OK", json.dumps({
            "trade_day": status["trade_day"],
            "screens_date": status["steps"]["build"].get("screens_date"),
            "etf_date": status["steps"]["build"].get("etf_date"),
        }, ensure_ascii=False))
        return 0
    except Exception as e:
        status["ok"] = False
        status["error"] = str(e)
        status["traceback"] = traceback.format_exc()
        status["finished"] = now_iso()
        write_status(status)
        print("refresh_daily FAIL", e)
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
