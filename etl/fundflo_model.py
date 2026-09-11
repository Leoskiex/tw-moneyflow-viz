"""FundFlo shared money-flow formulas (pure).

See docs/FUNDFLO_CONTRACT.md. WINDOW=5.
Curated foreign_net is 千張 (1e6 shares); foreign_flow_yi = shares * price / 1e8
= foreign_net * price / 100 when converting from curated.
"""
from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Sequence

WINDOW = 5

Number = Optional[float]


def _finite(x: Any) -> bool:
    try:
        return x is not None and math.isfinite(float(x))
    except (TypeError, ValueError):
        return False


def as_float(x: Any) -> Number:
    if not _finite(x):
        return None
    return float(x)


def clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def normalize(value: float, scale: float) -> float:
    """normalize(v,s)=clamp(asinh(v/s)/asinh(3),-1,1)"""
    s = scale if _finite(scale) and abs(float(scale)) > 0 else 1.0
    return clamp(math.asinh(float(value) / s) / math.asinh(3.0), -1.0, 1.0)


def shares_from_foreign_net_qianzhang(foreign_net: float) -> float:
    """curated foreign_net is 千張; 1 千張 = 1e6 股."""
    return float(foreign_net) * 1_000_000.0


def foreign_flow_yi_from_shares(shares: float, price: float) -> float:
    """shares (股) * price / 1e8 → 億元."""
    return float(shares) * float(price) / 1e8


def foreign_flow_yi_from_net(foreign_net_qianzhang: float, price: float) -> float:
    """Honest curated conversion: foreign_net(千張) * price / 100.

    Equivalent to shares_from_foreign_net_qianzhang * price / 1e8.
    Do NOT use foreign_net * price / 1e5 (that understates by 1000×).
    """
    return float(foreign_net_qianzhang) * float(price) / 100.0


def flow_of(day: Dict[str, Any], mode: str = "foreign") -> Number:
    if mode == "etf":
        return as_float(day.get("etf_flow_yi", day.get("etfFlow")))
    if mode == "combined":
        f = as_float(day.get("foreign_flow_yi", day.get("flow")))
        e = as_float(day.get("etf_flow_yi", day.get("etfFlow")))
        if f is None and e is None:
            return None
        return (f or 0.0) + (e or 0.0)
    return as_float(day.get("foreign_flow_yi", day.get("flow")))


def _window_indices(frame: int) -> tuple[int, int]:
    end = frame + WINDOW
    start = end - WINDOW + 1
    return start, end


def rolling_sum(days: Sequence[Dict[str, Any]], start: int, end: int, mode: str) -> Number:
    """Inclusive sum of flowOf over [start, end]. None if any day missing/non-finite."""
    if start < 0 or end >= len(days) or end - start + 1 != WINDOW:
        return None
    total = 0.0
    for i in range(start, end + 1):
        d = days[i]
        if d is None:
            return None
        v = flow_of(d, mode)
        if v is None:
            return None
        total += v
    return total


def rolling_ret_5d(days: Sequence[Dict[str, Any]], start: int, end: int) -> Number:
    """(close[end]/close[start-1]-1)*100 using adjustedClose or close."""
    if start < 1 or end >= len(days):
        return None
    end_day = days[end] or {}
    base_day = days[start - 1] or {}
    close = as_float(end_day.get("adjustedClose", end_day.get("adj_close", end_day.get("close"))))
    base = as_float(base_day.get("adjustedClose", base_day.get("adj_close", base_day.get("close"))))
    if close is None or base is None or base == 0:
        return None
    return (close / base - 1.0) * 100.0


def state(
    days: Sequence[Dict[str, Any]],
    frame: int,
    mode: str = "foreign",
) -> Optional[Dict[str, Any]]:
    """Compute rolling / momentum / ret for one stock series at frame.

    `days` is chronological daily dicts with foreign_flow_yi / etf_flow_yi / close.
    Returns None if the 5-day window is incomplete.
    """
    start, end = _window_indices(frame)
    if end >= len(days) or start < 0:
        return None
    rolling = rolling_sum(days, start, end, mode)
    if rolling is None:
        return None
    prior = rolling_sum(days, start - 1, end - 1, mode)
    prior_rolling = rolling if prior is None else prior
    today = days[end] or {}
    daily = flow_of(today, mode)
    foreign = as_float(today.get("foreign_flow_yi", today.get("flow")))
    etf = as_float(today.get("etf_flow_yi", today.get("etfFlow")))
    if etf is None:
        etf = 0.0
    shares = as_float(today.get("shares"))
    return {
        "flow": rolling,
        "rolling": rolling,
        "momentum": rolling - prior_rolling,
        "prior_rolling": prior_rolling,
        "rolling_ret": rolling_ret_5d(days, start, end),
        "daily_flow": daily,
        "foreign_flow_yi": foreign,
        "etf_flow_yi": etf,
        "combined_flow_yi": (foreign or 0.0) + etf if foreign is not None else (etf if daily is not None else None),
        "shares": shares,
        "close": as_float(today.get("close")),
        "start": start,
        "end": end,
    }


def enrich_day_metrics(history: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """For each day index that has a full WINDOW, attach rolling/momentum fields.

    Frame mapping: at day index `i` (end), frame = i - WINDOW; requires i >= WINDOW
    so that start-1 = i - WINDOW exists for returns when i >= WINDOW.
    We emit metrics when i >= WINDOW - 1 (full rolling window); momentum/ret need i >= WINDOW.
    """
    out: List[Dict[str, Any]] = []
    for i, day in enumerate(history):
        row = dict(day)
        foreign = as_float(row.get("foreign_flow_yi"))
        etf = as_float(row.get("etf_flow_yi"))
        if etf is None:
            etf = 0.0
            row["etf_flow_yi"] = 0.0
        if foreign is not None:
            row["combined_flow_yi"] = foreign + etf
        # Need WINDOW days ending at i → frame = i - WINDOW + 1? 
        # end = frame + WINDOW, we want end == i → frame = i - WINDOW
        # start = i - WINDOW + 1. For rolling only, need start >= 0 → i >= WINDOW - 1
        # For prior + ret, need start - 1 >= 0 → i >= WINDOW
        frame = i - WINDOW
        if frame < 0:
            # still allow rolling when i == WINDOW-1 (frame=-? no)
            # when i = WINDOW-1, frame = -1 invalid. So first rolling at i=WINDOW-1
            # with frame=0 requires end=5, so len at least 6 for frame 0...
            # Spec: end = frame + WINDOW, start = end - 4. For frame=0: start=1,end=5
            # That implies days[0] is history before first display frame.
            # For ETL by calendar day we treat chronological list where index 0 is oldest.
            # At calendar day i, use end=i, start=i-4, prior window start-1..end-1.
            pass

        end = i
        start = end - WINDOW + 1
        if start < 0:
            out.append(row)
            continue

        def _sum_mode(mode: str, a: int, b: int) -> Number:
            if a < 0:
                return None
            return rolling_sum(history, a, b, mode)

        for mode, rkey, mkey in (
            ("foreign", "rolling_foreign_5d_yi", "momentum_foreign_5d_yi"),
            ("combined", "rolling_combined_5d_yi", "momentum_combined_5d_yi"),
        ):
            rolling = _sum_mode(mode, start, end)
            if rolling is None:
                continue
            prior = _sum_mode(mode, start - 1, end - 1)
            prior_rolling = rolling if prior is None else prior
            row[rkey] = round(rolling, 6)
            row[mkey] = round(rolling - prior_rolling, 6)

        ret = rolling_ret_5d(history, start, end)
        if ret is not None:
            row["rolling_ret_5d"] = round(ret, 6)
        out.append(row)
    return out


def robust_scale(values: Iterable[float]) -> float:
    arr = sorted(abs(float(v)) for v in values if _finite(v))
    if not arr:
        return 1.0
    idx = min(len(arr) - 1, int(len(arr) * 0.85))
    return max(arr[idx], 0.01)


def ranked(
    stocks: Sequence[Dict[str, Any]],
    frame: int,
    count: int,
    direction: str = "both",
    mode: str = "foreign",
    days_key: str = "days",
) -> List[Dict[str, Any]]:
    """Rank stocks by |rolling| / buy / sell using state()."""
    scored = []
    for stock in stocks:
        days = stock.get(days_key) or []
        st = state(days, frame, mode)
        if not st:
            continue
        r = st["rolling"]
        if direction == "buy" and not (r > 0):
            continue
        if direction == "sell" and not (r < 0):
            continue
        scored.append((stock, st))
    if direction == "buy":
        scored.sort(key=lambda x: x[1]["rolling"], reverse=True)
    elif direction == "sell":
        scored.sort(key=lambda x: x[1]["rolling"])
    else:
        scored.sort(key=lambda x: abs(x[1]["rolling"]), reverse=True)
    return [{"stock": s, "state": st} for s, st in scored[:count]]


__all__ = [
    "WINDOW",
    "normalize",
    "clamp",
    "flow_of",
    "state",
    "rolling_sum",
    "rolling_ret_5d",
    "enrich_day_metrics",
    "shares_from_foreign_net_qianzhang",
    "foreign_flow_yi_from_shares",
    "foreign_flow_yi_from_net",
    "robust_scale",
    "ranked",
]
