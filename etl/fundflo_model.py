"""FundFlo shared money-flow formulas (pure).

See docs/FUNDFLO_CONTRACT.md. WINDOW=5.
Curated foreign_net is 千張 (1e6 shares); foreign_flow_yi = shares * price / 1e8
= foreign_net * price / 100 when converting from curated.

Modes: foreign | etf | combined | turnover
"""
from __future__ import annotations

import math
from typing import Any, Dict, Iterable, List, Optional, Sequence

WINDOW = 5

Number = Optional[float]

BLEND_KEYS = (
    "flow",
    "momentum",
    "rolling",
    "rolling_ret",
    "rollingRet",
    "daily_flow",
    "dailyFlow",
    "daily_ret",
    "dailyRet",
    "average5",
    "market_share",
    "marketShare",
    "turnover_change",
    "turnoverChange",
    "change_pct",
    "changePct",
    "foreign_flow_yi",
    "etf_flow_yi",
    "shares",
)


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


def ease(t: float) -> float:
    """Smoothstep ease used by FundFlo playback interpolation."""
    t = clamp(float(t), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


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
    if mode == "turnover":
        # ranking / size uses amount; chart x uses changePct via state()
        return as_float(day.get("amount"))
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
    if close is not None and base is not None and base != 0:
        return (close / base - 1.0) * 100.0
    # Fallback: chain daily change% over (start..end)
    prod = 1.0
    for i in range(start, end + 1):
        ch = as_float((days[i] or {}).get("change", (days[i] or {}).get("daily_ret")))
        if ch is None:
            return None
        prod *= 1.0 + ch / 100.0
    return (prod - 1.0) * 100.0


def _turnover_state(days: Sequence[Dict[str, Any]], frame: int) -> Optional[Dict[str, Any]]:
    """FundFlo turnover: flow=changePct, momentum=return, rolling=amount."""
    start, end = _window_indices(frame)
    if end >= len(days) or end < 0:
        return None
    today = days[end] or {}
    amount = as_float(today.get("amount"))
    average5 = as_float(today.get("average5", today.get("average_5")))
    change_pct = as_float(
        today.get("change_pct", today.get("changePct", today.get("turnover_change", today.get("turnoverChange"))))
    )
    market_share = as_float(today.get("market_share", today.get("marketShare")))
    daily_ret = as_float(today.get("daily_ret", today.get("dailyRet", today.get("return", today.get("change")))))
    cum_ret = as_float(
        today.get("cumulative_return", today.get("cumulativeReturn", today.get("rolling_ret_5d", today.get("rollingRet"))))
    )
    if cum_ret is None and start >= 1:
        cum_ret = rolling_ret_5d(days, start, end)
    if amount is None or not _finite(amount):
        return None
    # Prefer precomputed changePct; else derive from average5
    if change_pct is None and average5 is not None and average5 != 0:
        change_pct = (amount / average5 - 1.0) * 100.0
    if average5 is None and end >= WINDOW:
        prior = [as_float((days[i] or {}).get("amount")) for i in range(end - WINDOW, end)]
        if all(v is not None for v in prior):
            average5 = sum(prior) / float(WINDOW)  # type: ignore[arg-type]
            if change_pct is None and average5:
                change_pct = (amount / average5 - 1.0) * 100.0
    return {
        "flow": change_pct,
        "rolling": amount,
        "momentum": daily_ret,
        "prior_rolling": average5,
        "rolling_ret": cum_ret,
        "rollingRet": cum_ret,
        "daily_flow": amount,
        "dailyFlow": amount,
        "daily_ret": daily_ret,
        "dailyRet": daily_ret,
        "average5": average5,
        "market_share": market_share,
        "marketShare": market_share,
        "turnover_change": change_pct,
        "turnoverChange": change_pct,
        "change_pct": change_pct,
        "changePct": change_pct,
        "foreign_flow_yi": as_float(today.get("foreign_flow_yi", today.get("flow"))),
        "etf_flow_yi": as_float(today.get("etf_flow_yi", today.get("etfFlow"))) or 0.0,
        "shares": as_float(today.get("shares")),
        "close": as_float(today.get("close")),
        "start": start,
        "end": end,
    }


def state(
    days: Sequence[Dict[str, Any]],
    frame: int,
    mode: str = "foreign",
) -> Optional[Dict[str, Any]]:
    """Compute rolling / momentum / ret for one stock series at frame.

    `days` is chronological daily dicts with foreign_flow_yi / etf_flow_yi / close
    (or turnover fields). Returns None if the window / day is incomplete.
    """
    if mode == "turnover":
        return _turnover_state(days, frame)

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
    ret = rolling_ret_5d(days, start, end)
    return {
        "flow": rolling,
        "rolling": rolling,
        "momentum": rolling - prior_rolling,
        "prior_rolling": prior_rolling,
        "rolling_ret": ret,
        "rollingRet": ret,
        "daily_flow": daily,
        "dailyFlow": daily,
        "daily_ret": as_float(today.get("change", today.get("daily_ret"))),
        "dailyRet": as_float(today.get("change", today.get("daily_ret"))),
        "foreign_flow_yi": foreign,
        "etf_flow_yi": etf,
        "combined_flow_yi": (foreign or 0.0) + etf if foreign is not None else (etf if daily is not None else None),
        "shares": shares,
        "close": as_float(today.get("close")),
        "start": start,
        "end": end,
    }


def interpolate_state(
    a: Optional[Dict[str, Any]],
    b: Optional[Dict[str, Any]],
    t: float,
    use_ease: bool = True,
) -> Optional[Dict[str, Any]]:
    """Blend two state() dicts for fractional frame playback.

    UI blending keys: flow, momentum, rolling, rollingRet/rolling_ret,
    average5, marketShare/market_share, turnoverChange/turnover_change.
    """
    if a is None and b is None:
        return None
    if a is None:
        return dict(b) if b else None
    if b is None:
        return dict(a)
    tt = ease(t) if use_ease else clamp(float(t), 0.0, 1.0)
    out = dict(a)
    keys = set(a) | set(b)
    for key in keys:
        va, vb = a.get(key), b.get(key)
        if _finite(va) and _finite(vb):
            out[key] = float(va) + (float(vb) - float(va)) * tt
        elif _finite(vb):
            out[key] = float(vb)
        elif _finite(va):
            out[key] = float(va)
        else:
            out[key] = vb if vb is not None else va
    # Keep camelCase aliases in sync when present
    if "rolling_ret" in out and "rollingRet" not in out:
        out["rollingRet"] = out["rolling_ret"]
    if "rollingRet" in out and "rolling_ret" not in out:
        out["rolling_ret"] = out["rollingRet"]
    if "turnover_change" in out:
        out["turnoverChange"] = out["turnover_change"]
        out["changePct"] = out["turnover_change"]
        out["change_pct"] = out["turnover_change"]
    if "market_share" in out:
        out["marketShare"] = out["market_share"]
    return out


def enrich_day_metrics(history: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """For each day index that has a full WINDOW, attach rolling/momentum fields."""
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
            ("etf", "rolling_etf_5d_yi", "momentum_etf_5d_yi"),
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
            if row.get("cumulative_return") is None and row.get("cumulativeReturn") is None:
                row["cumulative_return"] = round(ret, 6)
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
    """Rank stocks by |rolling| / buy / sell / turnover fields using state()."""
    scored = []
    for stock in stocks:
        days = stock.get(days_key) or []
        st = state(days, frame, mode)
        if not st:
            continue
        if mode == "turnover":
            if direction == "surge":
                field = "turnoverChange"
            elif direction == "share":
                field = "marketShare"
            else:
                field = "rolling"
            val = st.get(field)
            if not _finite(val):
                continue
            scored.append((stock, st, float(val)))
            continue
        r = st["rolling"]
        if direction == "buy" and not (r > 0):
            continue
        if direction == "sell" and not (r < 0):
            continue
        scored.append((stock, st, float(r)))

    if mode == "turnover":
        scored.sort(key=lambda x: x[2], reverse=True)
    elif direction == "buy":
        scored.sort(key=lambda x: x[1]["rolling"], reverse=True)
    elif direction == "sell":
        scored.sort(key=lambda x: x[1]["rolling"])
    else:
        scored.sort(key=lambda x: abs(x[1]["rolling"]), reverse=True)
    return [{"stock": s, "state": st} for s, st, _ in scored[:count]]


__all__ = [
    "WINDOW",
    "BLEND_KEYS",
    "normalize",
    "clamp",
    "ease",
    "flow_of",
    "state",
    "interpolate_state",
    "rolling_sum",
    "rolling_ret_5d",
    "enrich_day_metrics",
    "shares_from_foreign_net_qianzhang",
    "foreign_flow_yi_from_shares",
    "foreign_flow_yi_from_net",
    "robust_scale",
    "ranked",
]
