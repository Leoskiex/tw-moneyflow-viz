#!/usr/bin/env python3
"""Extra deterministic screens used by build_screens.build_day — no LLM."""
from __future__ import annotations

from typing import Any, Optional

# thresholds
FH_HIGH = 25.0
FH_LOW = 15.0
FOREIGN_FLOW = 1.0
LEV_MARGIN = 0.40
LEV_FOREIGN = -1.0
SBL_LOW = 100.0
SBL_HIGH = 2000.0
SHORT_PRESS = 50.0
THEME_DELTA = 8.0
ALIGN_F, ALIGN_T = 0.5, 0.3
CONFLICT_ABS = 0.5
DAYTRADE_HOT = 40.0
NOISE_CHG, NOISE_AMT = 3.0, 1.0
SPLIT_ABS = 20.0  # 億


def _n(x: Any, d: float = 0.0) -> float:
    try:
        return d if x is None else float(x)
    except (TypeError, ValueError):
        return d


def screen_foreign_stock_flow(stocks, is_etf, stock_row) -> dict:
    acc, fresh, dist = [], [], []
    for s in stocks:
        if is_etf(s):
            continue
        fh = s.get("foreign_hold_pct")
        if fh is None:
            continue
        fh = _n(fh)
        fn = _n(s.get("foreign_net"))
        if fh >= FH_HIGH and fn >= FOREIGN_FLOW:
            sc = abs(fn) * (1 + fh / 100.0)
            acc.append(stock_row(s, extra={
                "screen": "accumulation", "score": round(sc, 3),
                "bucket": "accumulation",
                "why": [f"外资持股 {fh:.1f}%≥{FH_HIGH}% 且外资净买 {fn:.2f} 千张（高水位续买）"],
            }))
        elif fh < FH_LOW and fn >= FOREIGN_FLOW:
            sc = abs(fn) * (1 + (FH_LOW - fh) / 100.0)
            fresh.append(stock_row(s, extra={
                "screen": "fresh_money", "score": round(sc, 3),
                "bucket": "fresh_money",
                "why": [f"外资持股 {fh:.1f}%<{FH_LOW}% 且外资净买 {fn:.2f}（低水位新进）"],
            }))
        elif fh >= FH_HIGH and fn <= -FOREIGN_FLOW:
            sc = abs(fn) * (1 + fh / 100.0)
            dist.append(stock_row(s, extra={
                "screen": "distribution", "score": round(sc, 3),
                "bucket": "distribution",
                "why": [f"外资持股 {fh:.1f}%≥{FH_HIGH}% 且外资净卖 {fn:.2f}（高水位出货）"],
            }))
    for lst in (acc, fresh, dist):
        lst.sort(key=lambda r: r["score"], reverse=True)
    return {
        "accumulation": acc[:30],
        "fresh_money": fresh[:30],
        "distribution": dist[:30],
    }


def screen_leverage_pressure(stocks, is_etf, stock_row) -> dict:
    traps, delever = [], []
    for s in stocks:
        if is_etf(s):
            continue
        fn = _n(s.get("foreign_net"))
        mu = _n(s.get("margin_util"))
        md = s.get("margin_delta")
        if fn <= LEV_FOREIGN and mu >= LEV_MARGIN and (md is None or _n(md) >= 0):
            sc = abs(fn) * 5 + mu * 20
            traps.append(stock_row(s, extra={
                "screen": "leverage_trap", "score": round(sc, 3),
                "bucket": "leverage_trap",
                "why": [f"外资卖 {fn:.2f} + 融资使用率 {mu*100:.1f}%≥{LEV_MARGIN*100:.0f}%（杠杆接力风险）"],
            }))
        if fn >= 1.0 and md is not None and _n(md) < 0:
            sc = fn * 5 + abs(_n(md)) / 1000.0
            delever.append(stock_row(s, extra={
                "screen": "delever_with_flow", "score": round(sc, 3),
                "bucket": "delever_with_flow",
                "why": [f"外资买 {fn:.2f} 且融资余额Δ {md}（有流且去杠杆）"],
            }))
    traps.sort(key=lambda r: r["score"], reverse=True)
    delever.sort(key=lambda r: r["score"], reverse=True)
    return {"leverage_trap": traps[:30], "delever_with_flow": delever[:30]}


def screen_short_ammo(stocks, is_etf, stock_row) -> dict:
    squeeze, fuel = [], []
    for s in stocks:
        if is_etf(s):
            continue
        avail = s.get("sbl_avail")
        sbl = _n(s.get("sbl_sell"))
        sh = _n(s.get("short_sell"))
        util = s.get("short_util")
        press = sbl + sh
        if avail is not None and _n(avail) < SBL_LOW and press >= SHORT_PRESS:
            sc = press / max(_n(avail), 1.0)
            squeeze.append(stock_row(s, extra={
                "screen": "squeeze_risk", "score": round(sc, 3),
                "bucket": "squeeze_risk",
                "why": [f"可借券 {avail} 张偏低 + 空方卖压 {press:.0f}（挤空敏感）"],
            }))
        fuel_ok = False
        why = ""
        if avail is not None and _n(avail) >= SBL_HIGH:
            if util is not None and _n(util) >= 0.5:
                fuel_ok, why = True, f"可借 {avail} 高 + 融券使用率 {_n(util)*100:.1f}%"
            elif sbl >= 100:
                fuel_ok, why = True, f"可借 {avail} 高 + 借券卖出 {sbl:.0f}"
        if fuel_ok:
            sc = _n(avail) / 1000.0 + sbl / 50.0 + (_n(util) if util is not None else 0) * 10
            fuel.append(stock_row(s, extra={
                "screen": "fuel_for_shorts", "score": round(sc, 3),
                "bucket": "fuel_for_shorts",
                "why": [why + "（空方弹药充足）"],
            }))
    squeeze.sort(key=lambda r: r["score"], reverse=True)
    fuel.sort(key=lambda r: r["score"], reverse=True)
    return {"squeeze_risk": squeeze[:30], "fuel_for_shorts": fuel[:30]}


def screen_disposal_countdown(stocks, is_etf, stock_row) -> list:
    rows = []
    for s in stocks:
        if is_etf(s):
            continue
        streak = int(_n(s.get("notice_streak")))
        risk = s.get("disp_risk") or "none"
        if s.get("disposition"):
            cd, status, path = 0, "disposed", "官方处置"
        elif risk == "high" or streak >= 3:
            cd, status, path = 1, "danger", s.get("disp_risk_reason") or f"notice_streak={streak}"
        elif streak == 2 or risk == "med":
            cd, status, path = 2, "near", s.get("disp_risk_reason") or f"notice_streak={streak}"
        elif s.get("notice") or streak == 1:
            cd, status, path = 3, "watch", s.get("disp_risk_reason") or "注意／streak1"
        else:
            continue
        sc = (4 - cd) * 10 + streak
        rows.append(stock_row(s, extra={
            "screen": "disposal_countdown",
            "score": round(sc, 3),
            "countdown": cd,
            "status": status,
            "path": path,
            "why": [f"countdown={cd} status={status} | {path}"],
        }))
    rows.sort(key=lambda r: (r.get("countdown", 9), -r["score"]))
    return rows[:40]


def theme_nets_from_day(day, topic_of, inst_net, is_etf) -> dict:
    out = {}
    for s in day.get("stocks") or []:
        if is_etf(s):
            continue
        # prefer curated topics list if present
        pass
    # Prefer official topic aggregates when available
    for t in day.get("topics") or []:
        name = t.get("shortname") or t.get("name") or t.get("id")
        if not name:
            continue
        out[str(name)] = _n(t.get("inst_net"))
    if out:
        return out
    for s in day.get("stocks") or []:
        if is_etf(s):
            continue
        name = topic_of(s)
        if name == "未對應":
            continue
        out[name] = out.get(name, 0.0) + inst_net(s)
    return out


def screen_theme_rotation(today_nets: dict, hist_nets: list[dict]) -> dict:
    """hist_nets: list of prior day theme→net maps, oldest first."""
    accel, fade = [], []
    if not today_nets:
        return {"theme_acceleration": [], "theme_fade": []}
    keys = set(today_nets)
    for h in hist_nets:
        keys |= set(h)
    for topic in keys:
        today = today_nets.get(topic, 0.0)
        prev_vals = [h.get(topic, 0.0) for h in hist_nets if topic in h or True]
        # use last up to 3
        prev_vals = [h.get(topic, 0.0) for h in hist_nets[-3:]]
        if not hist_nets:
            continue
        prev_mean = sum(prev_vals) / max(len(prev_vals), 1)
        delta = today - prev_mean
        if today > 0 and delta >= THEME_DELTA:
            accel.append({
                "topic": topic,
                "inst_net": round(today, 3),
                "prev_mean": round(prev_mean, 3),
                "delta": round(delta, 3),
                "score": round(delta, 3),
                "screen": "theme_acceleration",
                "why": [f"今日 {today:.1f} vs 近{len(prev_vals)}日均 {prev_mean:.1f}（加速 +{delta:.1f} 千张）"],
            })
        fade_hit = (today < 0 and delta <= -THEME_DELTA) or (
            prev_mean > 10 and today < prev_mean * 0.3
        )
        if fade_hit and (today < prev_mean):
            fade.append({
                "topic": topic,
                "inst_net": round(today, 3),
                "prev_mean": round(prev_mean, 3),
                "delta": round(delta, 3),
                "score": round(abs(delta), 3),
                "screen": "theme_fade",
                "why": [f"今日 {today:.1f} vs 近均 {prev_mean:.1f}（褪色 Δ{delta:.1f}）"],
            })
    accel.sort(key=lambda r: r["score"], reverse=True)
    fade.sort(key=lambda r: r["score"], reverse=True)
    return {"theme_acceleration": accel[:20], "theme_fade": fade[:20]}


def screen_inst_alignment(stocks, is_etf, stock_row) -> dict:
    aligned, conflict = [], []
    for s in stocks:
        if is_etf(s):
            continue
        f, t, d = _n(s.get("foreign_net")), _n(s.get("trust_net")), _n(s.get("dealer_net"))
        if f >= ALIGN_F and t >= ALIGN_T and d >= 0:
            sc = min(f, t * 2) + max(d, 0)
            aligned.append(stock_row(s, extra={
                "screen": "aligned_bid", "score": round(sc, 3),
                "bucket": "aligned_bid",
                "why": [f"外资 {f:.2f}/投信 {t:.2f}/自营 {d:.2f} 同向买"],
            }))
        legs = [("外资", f), ("投信", t), ("自营", d)]
        big = [(n, v) for n, v in legs if abs(v) >= CONFLICT_ABS]
        if len(big) >= 2:
            signs = {1 if v > 0 else -1 for _, v in big}
            if len(signs) > 1:
                sc = sum(abs(v) for _, v in big)
                conflict.append(stock_row(s, extra={
                    "screen": "conflict", "score": round(sc, 3),
                    "bucket": "conflict",
                    "why": [f"法人打架：" + "，".join(f"{n} {v:.2f}" for n, v in big)],
                }))
    aligned.sort(key=lambda r: r["score"], reverse=True)
    conflict.sort(key=lambda r: r["score"], reverse=True)
    return {"aligned_bid": aligned[:30], "conflict": conflict[:30]}


def screen_daytrade_noise(stocks, market_kpi, is_etf, stock_row) -> tuple[list, bool]:
    hot = _n(market_kpi.get("daytrade_pct")) >= DAYTRADE_HOT
    rows = []
    if not hot:
        return rows, False
    for s in stocks:
        if is_etf(s):
            continue
        inst = _n(s.get("inst_net"))
        if s.get("inst_net") is None:
            inst = _n(s.get("foreign_net")) + _n(s.get("trust_net")) + _n(s.get("dealer_net"))
        chg = abs(_n(s.get("change")))
        amt = _n(s.get("amount"))
        if abs(inst) < 1.0 and chg >= NOISE_CHG and amt >= NOISE_AMT:
            sc = chg * amt
            rows.append(stock_row(s, extra={
                "screen": "daytrade_noise", "score": round(sc, 3),
                "why": [f"当冲市况 {market_kpi.get('daytrade_pct')}% + 涨跌 {chg:.1f}% 但法人弱 {inst:.2f}"],
            }))
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows[:40], True


def market_split(market_kpi: dict) -> dict:
    listed = _n(market_kpi.get("foreign_net"))
    tpex = _n(market_kpi.get("tpex_foreign_net"))
    if listed >= SPLIT_ABS and tpex >= SPLIT_ABS:
        label, why = "both_push", f"上市外资 {listed:.1f} 与柜买 {tpex:.1f} 同向大买"
    elif listed <= -SPLIT_ABS and tpex <= -SPLIT_ABS:
        label, why = "both_risk_off", f"上市 {listed:.1f} 与柜买 {tpex:.1f} 同向大卖"
    elif listed * tpex < 0 and abs(listed) >= SPLIT_ABS and abs(tpex) >= SPLIT_ABS:
        label, why = "split", f"上市外资 {listed:.1f} 与柜买 {tpex:.1f} 反向（市场分裂）"
    elif abs(listed) < 20 and abs(tpex) < 20:
        label, why = "quiet", f"上市/柜买外资变动都不大（{listed:.1f}/{tpex:.1f}）"
    else:
        label, why = "aligned", f"上市 {listed:.1f}／柜买 {tpex:.1f}（未达分裂门槛）"
    return {
        "label": label,
        "listed_foreign": round(listed, 3),
        "tpex_foreign": round(tpex, 3),
        "why": why,
    }


def noise_codes(noise_rows: list) -> set:
    return {r.get("code") for r in noise_rows}
