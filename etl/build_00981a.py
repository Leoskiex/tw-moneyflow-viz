#!/usr/bin/env python3
"""00981A holdings Δ + cross with screens / regime.

Inputs:
  holdings snapshots from fetch_00981a.py
  data/screens_latest.json (or screens/<date>.json)
  data/regime_latest.json

Δ source priority:
  1) previous local holdings file (same schema)
  2) JoJoRadar stock_trend per code (bootstrap; exits only with local prev)

Writes:
  data/etf/00981a/<date>.json
  data/etf/00981a/latest.json
"""
from __future__ import annotations

import json
import ssl
import time
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

import fetch_00981a as f981

VIZ = Path("/workspace/tw-moneyflow-viz/data")
OUT_DIR = VIZ / "etf" / "00981a"
OUT_LATEST = OUT_DIR / "latest.json"
SCREENS_DIR = VIZ / "screens"
SCREENS_LATEST = VIZ / "screens_latest.json"
REGIME_LATEST = VIZ / "regime_latest.json"
JOJO_TREND = "https://www.jojoradar.com/api/00981A/stock_trend/{code}"
UA = "Mozilla/5.0 (compatible; tw-moneyflow/1.0; +local)"
TZ8 = timezone(timedelta(hours=8))


def _now_iso() -> str:
    return datetime.now(TZ8).isoformat(timespec="seconds")


def _num(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except (TypeError, ValueError):
        return default


def _fetch_json(url: str, timeout: int = 25) -> Any:
    import subprocess
    r = subprocess.run(
        [
            "curl", "-skL", "--max-time", str(timeout),
            "-A", UA,
            "-H", "Accept: application/json,*/*",
            url,
        ],
        capture_output=True,
        check=False,
    )
    if r.returncode != 0 or not r.stdout:
        raise RuntimeError(f"curl json failed rc={r.returncode}")
    return json.loads(r.stdout.decode("utf-8", errors="replace"))


def load_screens(date: str) -> Optional[dict[str, Any]]:
    p = SCREENS_DIR / f"{date}.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    if SCREENS_LATEST.exists():
        j = json.loads(SCREENS_LATEST.read_text(encoding="utf-8"))
        if j.get("date") == date:
            return j
    return None


def load_regime(date: str) -> Optional[dict[str, Any]]:
    if REGIME_LATEST.exists():
        j = json.loads(REGIME_LATEST.read_text(encoding="utf-8"))
        if j.get("date") == date:
            return j
    regimes = VIZ / "regimes.json"
    if regimes.exists():
        payload = json.loads(regimes.read_text(encoding="utf-8"))
        for d in payload.get("days") or []:
            if d.get("date") == date:
                return d
    return None


def _index_holdings(doc: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(h["code"]): h for h in (doc.get("holdings") or [])}


def delta_from_local(cur: dict[str, Any], prev: dict[str, Any]) -> dict[str, Any]:
    c_map = _index_holdings(cur)
    p_map = _index_holdings(prev)
    adds, cuts, new, exited = [], [], [], []
    for code, h in c_map.items():
        if code not in p_map:
            new.append(
                {
                    "code": code,
                    "name": h["name"],
                    "share": h["share"],
                    "weight_pct": h["weight_pct"],
                    "share_delta": h["share"],
                    "weight_delta": h["weight_pct"],
                    "action": "new",
                }
            )
            continue
        ph = p_map[code]
        sd = h["share"] - ph["share"]
        wd = h["weight_pct"] - ph["weight_pct"]
        row = {
            "code": code,
            "name": h["name"],
            "share": h["share"],
            "weight_pct": h["weight_pct"],
            "prev_share": ph["share"],
            "prev_weight_pct": ph["weight_pct"],
            "share_delta": sd,
            "weight_delta": round(wd, 4),
        }
        if sd > 0 or wd > 0.05:
            row["action"] = "add"
            adds.append(row)
        elif sd < 0 or wd < -0.05:
            row["action"] = "cut"
            cuts.append(row)
    for code, ph in p_map.items():
        if code not in c_map:
            exited.append(
                {
                    "code": code,
                    "name": ph["name"],
                    "prev_share": ph["share"],
                    "prev_weight_pct": ph["weight_pct"],
                    "share_delta": -ph["share"],
                    "weight_delta": -ph["weight_pct"],
                    "action": "exit",
                }
            )
    adds.sort(key=lambda x: (-abs(x.get("share_delta") or 0), -abs(x.get("weight_delta") or 0)))
    cuts.sort(key=lambda x: (x.get("share_delta") or 0, x.get("weight_delta") or 0))
    new.sort(key=lambda x: -x["weight_pct"])
    exited.sort(key=lambda x: -x["prev_weight_pct"])
    return {
        "prev_date": prev.get("date"),
        "source": "local_snapshot",
        "adds": adds,
        "cuts": cuts,
        "new": new,
        "exits": exited,
    }


def jojo_prior_row(code: str, as_of: str) -> Optional[dict[str, Any]]:
    """Return (as_of row, previous row) from JoJoRadar trend, or None."""
    try:
        j = _fetch_json(JOJO_TREND.format(code=code))
    except Exception:
        return None
    rows = j.get("rows") or []
    by_date = {r.get("date"): r for r in rows if r.get("date")}
    if as_of not in by_date:
        # take last row on or before as_of
        dates = sorted(d for d in by_date if d <= as_of)
        if not dates:
            return None
        as_of = dates[-1]
    cur = by_date[as_of]
    earlier = sorted(d for d in by_date if d < as_of)
    prev = by_date[earlier[-1]] if earlier else None
    return {"as_of": as_of, "cur": cur, "prev": prev, "desc": j.get("latest_change_desc")}


def delta_from_jojo(cur: dict[str, Any], sleep_s: float = 0.05) -> dict[str, Any]:
    date = cur["date"]
    adds, cuts, new, flat = [], [], [], []
    missed = 0
    for i, h in enumerate(cur.get("holdings") or []):
        code = h["code"]
        pack = jojo_prior_row(code, date)
        if sleep_s:
            time.sleep(sleep_s)
        if not pack or not pack.get("prev"):
            missed += 1
            flat.append({"code": code, "name": h["name"], "note": "no_jojo_prev"})
            continue
        pc, pp = pack["cur"], pack["prev"]
        share = _num(pc.get("shares_qty"), h["share"])
        prev_share = _num(pp.get("shares_qty"), share)
        # null shares historically → treat as new
        if pp.get("shares_qty") is None and pc.get("shares_qty") is not None:
            new.append(
                {
                    "code": code,
                    "name": h["name"],
                    "share": share,
                    "weight_pct": h["weight_pct"],
                    "share_delta": share,
                    "weight_delta": h["weight_pct"],
                    "action": "new",
                    "jojo_prev_date": pp.get("date"),
                }
            )
            continue
        sd = share - prev_share
        wd = _num(pc.get("weight_pct")) - _num(pp.get("weight_pct"))
        row = {
            "code": code,
            "name": h["name"],
            "share": h["share"],
            "weight_pct": h["weight_pct"],
            "prev_share": prev_share,
            "prev_weight_pct": _num(pp.get("weight_pct")),
            "share_delta": sd,
            "weight_delta": round(wd, 4),
            "jojo_prev_date": pp.get("date"),
            "jojo_desc": pack.get("desc"),
        }
        if sd > 500 or wd > 0.05:  # share threshold ~500 shares
            row["action"] = "add"
            adds.append(row)
        elif sd < -500 or wd < -0.05:
            row["action"] = "cut"
            cuts.append(row)
        else:
            row["action"] = "flat"
            flat.append(row)
        if (i + 1) % 10 == 0:
            print(f"  jojo trend {i+1}/{len(cur.get('holdings') or [])}")
    adds.sort(key=lambda x: (-abs(x.get("share_delta") or 0), -abs(x.get("weight_delta") or 0)))
    cuts.sort(key=lambda x: (x.get("share_delta") or 0, x.get("weight_delta") or 0))
    return {
        "prev_date": None,
        "source": "jojoradar_stock_trend",
        "note": "exits unavailable without prior full snapshot; share/weight Δ from JoJoRadar",
        "missed": missed,
        "adds": adds,
        "cuts": cuts,
        "new": new,
        "exits": [],
        "flat_n": len(flat),
    }


def _codeset(rows: list[dict[str, Any]]) -> set[str]:
    out = set()
    for r in rows or []:
        c = str(r.get("code") or "")
        if c:
            out.add(c)
    return out


def _theme_accel_topics(screens: dict[str, Any]) -> set[str]:
    rot = screens.get("theme_rotation") or {}
    return {str(t.get("topic") or "") for t in (rot.get("theme_acceleration") or []) if t.get("topic")}


def cross_screens(
    holdings: list[dict[str, Any]],
    screens: Optional[dict[str, Any]],
    regime: Optional[dict[str, Any]],
    flow: dict[str, Any],
) -> dict[str, Any]:
    if not screens:
        return {
            "intersect_mild_push": [],
            "intersect_theme_accel": [],
            "flag_exit_watch": [],
            "aligned_with_regime": [],
            "note": "screens missing for date",
        }

    mild = {r["code"]: r for r in (screens.get("mild_push") or [])}
    exitw = {r["code"]: r for r in (screens.get("exit_watch") or [])}
    heavy = {r["code"]: r for r in (screens.get("heavy_push_contrast") or [])}
    accel_topics = _theme_accel_topics(screens)
    themes_in = {str(t.get("topic") or t) if isinstance(t, dict) else str(t) for t in (screens.get("themes_in") or [])}

    # map code -> topic from any screen row or curated not available here
    topic_by: dict[str, str] = {}
    for bucket in (mild, exitw, heavy):
        for c, r in bucket.items():
            if r.get("topic"):
                topic_by[c] = r["topic"]

    h_by = {h["code"]: h for h in holdings}
    flow_by = {}
    for key in ("adds", "cuts", "new", "exits"):
        for r in flow.get(key) or []:
            flow_by[r["code"]] = r

    intersect_mild = []
    for code, h in h_by.items():
        if code in mild:
            s = mild[code]
            fr = flow_by.get(code) or {}
            intersect_mild.append(
                {
                    "code": code,
                    "name": h["name"],
                    "weight_pct": h["weight_pct"],
                    "share_delta": fr.get("share_delta"),
                    "weight_delta": fr.get("weight_delta"),
                    "action": fr.get("action"),
                    "topic": s.get("topic"),
                    "inst_net": s.get("inst_net"),
                    "screen_score": s.get("score"),
                    "why": (s.get("why") or [])[:2],
                }
            )
    intersect_mild.sort(key=lambda x: (-(x.get("weight_pct") or 0), -(x.get("screen_score") or 0)))

    intersect_accel = []
    for code, h in h_by.items():
        topic = topic_by.get(code) or ""
        # also match themes_in if acceleration empty for code's topic from mild/heavy
        if topic and topic in accel_topics:
            fr = flow_by.get(code) or {}
            s = mild.get(code) or heavy.get(code) or exitw.get(code) or {}
            intersect_accel.append(
                {
                    "code": code,
                    "name": h["name"],
                    "weight_pct": h["weight_pct"],
                    "topic": topic,
                    "share_delta": fr.get("share_delta"),
                    "weight_delta": fr.get("weight_delta"),
                    "action": fr.get("action"),
                    "inst_net": s.get("inst_net"),
                }
            )
    # if no topic map for holdings, use themes_in ∩ holdings via mild/heavy only already done
    # enrich: holdings whose screen topic is in themes_in even if not in accel list
    if not intersect_accel and themes_in:
        for code, h in h_by.items():
            topic = topic_by.get(code) or ""
            if topic in themes_in:
                fr = flow_by.get(code) or {}
                s = mild.get(code) or heavy.get(code) or {}
                intersect_accel.append(
                    {
                        "code": code,
                        "name": h["name"],
                        "weight_pct": h["weight_pct"],
                        "topic": topic,
                        "share_delta": fr.get("share_delta"),
                        "weight_delta": fr.get("weight_delta"),
                        "action": fr.get("action"),
                        "inst_net": s.get("inst_net"),
                        "note": "theme in themes_in (accel list empty/miss)",
                    }
                )
    intersect_accel.sort(key=lambda x: (-(x.get("weight_pct") or 0)))

    flag_exit = []
    for code, h in h_by.items():
        if code in exitw:
            s = exitw[code]
            fr = flow_by.get(code) or {}
            flag_exit.append(
                {
                    "code": code,
                    "name": h["name"],
                    "weight_pct": h["weight_pct"],
                    "share_delta": fr.get("share_delta"),
                    "weight_delta": fr.get("weight_delta"),
                    "action": fr.get("action"),
                    "topic": s.get("topic"),
                    "inst_net": s.get("inst_net"),
                    "screen_score": s.get("score"),
                    "why": (s.get("why") or [])[:2],
                }
            )
    flag_exit.sort(key=lambda x: (-(x.get("weight_pct") or 0)))

    aligned = []
    primary = (regime or {}).get("primary")
    top_topic = ((regime or {}).get("metrics") or {}).get("top_topic") or (regime or {}).get("top_topic")
    if primary == "inst_push" and top_topic:
        for code, h in h_by.items():
            topic = topic_by.get(code) or ""
            if topic == top_topic:
                fr = flow_by.get(code) or {}
                s = mild.get(code) or heavy.get(code) or {}
                aligned.append(
                    {
                        "code": code,
                        "name": h["name"],
                        "weight_pct": h["weight_pct"],
                        "topic": topic,
                        "regime_primary": primary,
                        "share_delta": fr.get("share_delta"),
                        "weight_delta": fr.get("weight_delta"),
                        "action": fr.get("action"),
                        "inst_net": s.get("inst_net"),
                    }
                )
        aligned.sort(key=lambda x: (-(x.get("weight_pct") or 0)))

    return {
        "intersect_mild_push": intersect_mild,
        "intersect_theme_accel": intersect_accel,
        "flag_exit_watch": flag_exit,
        "aligned_with_regime": aligned,
        "accel_topics": sorted(accel_topics),
        "regime_top_topic": top_topic,
    }


def build(use_jojo_if_needed: bool = True) -> dict[str, Any]:
    # ensure fresh fetch
    try:
        fetched = f981.fetch_and_save()
        print("fetched", fetched)
    except Exception as e:
        print(f"WARNING: live fetch failed ({e}); using latest snapshot")
        fetched = None

    cur = f981.load_holdings()
    if not cur:
        raise SystemExit("no 00981A holdings snapshot available")

    date = cur["date"]
    dates = f981.list_saved_dates()
    prev_doc = None
    for d in reversed(dates):
        if d < date:
            prev_doc = f981.load_holdings(d)
            break

    if prev_doc:
        flow = delta_from_local(cur, prev_doc)
    elif use_jojo_if_needed:
        print("no local prev day — bootstrapping Δ via JoJoRadar stock_trend…")
        flow = delta_from_jojo(cur)
    else:
        flow = {
            "prev_date": None,
            "source": "none",
            "adds": [],
            "cuts": [],
            "new": [],
            "exits": [],
            "note": "single snapshot; Δ skipped",
        }

    screens = load_screens(date)
    regime = load_regime(date)
    cross = cross_screens(cur.get("holdings") or [], screens, regime, flow)

    # attach topic from screens onto full holdings for UI
    topic_by = {}
    if screens:
        for key in ("mild_push", "exit_watch", "heavy_push_contrast"):
            for r in screens.get(key) or []:
                if r.get("code") and r.get("topic"):
                    topic_by[r["code"]] = r["topic"]
    holdings_out = []
    for h in cur.get("holdings") or []:
        row = dict(h)
        row["topic"] = topic_by.get(h["code"])
        fr = None
        for key in ("adds", "cuts", "new", "exits"):
            for r in flow.get(key) or []:
                if r["code"] == h["code"]:
                    fr = r
                    break
            if fr:
                break
        if fr:
            row["share_delta"] = fr.get("share_delta")
            row["weight_delta"] = fr.get("weight_delta")
            row["action"] = fr.get("action")
        holdings_out.append(row)

    payload = {
        "date": date,
        "etf": "00981A",
        "name": "統一投信 00981A（日揭持股）",
        "generated_at": _now_iso(),
        "source": cur.get("source"),
        "source_url": cur.get("source_url"),
        "meta": cur.get("meta"),
        "regime": {
            "primary": (regime or {}).get("primary"),
            "primary_label": (regime or {}).get("primary_label"),
            "secondary": (regime or {}).get("secondary"),
            "secondary_label": (regime or {}).get("secondary_label"),
            "top_topic": ((regime or {}).get("metrics") or {}).get("top_topic"),
        }
        if regime
        else None,
        "manager_flow": {
            "prev_date": flow.get("prev_date"),
            "source": flow.get("source"),
            "note": flow.get("note"),
            "counts": {
                "adds": len(flow.get("adds") or []),
                "cuts": len(flow.get("cuts") or []),
                "new": len(flow.get("new") or []),
                "exits": len(flow.get("exits") or []),
            },
            "adds": (flow.get("adds") or [])[:20],
            "cuts": (flow.get("cuts") or [])[:20],
            "new": (flow.get("new") or [])[:20],
            "exits": (flow.get("exits") or [])[:20],
        },
        "cross": cross,
        "holdings": holdings_out,
        "disclaimer": "日揭持股非即時；Δ 來自本地前日或 JoJoRadar；交叉为启发式，非投资建议",
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / f"{date}.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_LATEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"wrote {OUT_LATEST} holdings={len(holdings_out)} mild∩={len(cross['intersect_mild_push'])} exit∩={len(cross['flag_exit_watch'])}")
    return payload


def main() -> None:
    build(use_jojo_if_needed=True)


if __name__ == "__main__":
    main()
