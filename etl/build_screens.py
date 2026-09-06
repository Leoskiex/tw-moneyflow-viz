#!/usr/bin/env python3
"""
Deterministic stock screens from curated day JSON — no LLM.

Writes:
  /workspace/tw-moneyflow-viz/data/screens/<date>.json
  /workspace/tw-moneyflow-viz/data/screens_latest.json
  /workspace/tw-moneyflow-viz/data/screens_index.json

Screens:
  mild_push  — light institutional buy in inflow themes, no regulatory flags
  exit_watch — outflow themes / foreign-sell+high-margin / disposition risk
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

import screens_extra as sx

CURATED_DIR = Path("/workspace/tw-moneyflow-viz/data/curated")
REGIME_LATEST = Path("/workspace/tw-moneyflow-viz/data/regime_latest.json")
REGIMES = Path("/workspace/tw-moneyflow-viz/data/regimes.json")
OUT_DIR = Path("/workspace/tw-moneyflow-viz/data/screens")
OUT_LATEST = Path("/workspace/tw-moneyflow-viz/data/screens_latest.json")
OUT_INDEX = Path("/workspace/tw-moneyflow-viz/data/screens_index.json")

# --- tunable thresholds (units: 千张 for inst nets unless noted) ---
MILD_PUSH_MIN = 0.5
MILD_PUSH_MAX = 8.0
TOPIC_INFLOW_TOP_N = 5
TOPIC_OUTFLOW_TOP_N = 5
TOPIC_FLOW_MIN_ABS = 3.0  # ignore tiny theme nets when ranking
EXIT_INST_SELL = -1.0
EXIT_FOREIGN_SELL = -2.0
EXIT_MARGIN_UTIL = 0.50  # 50%
HEAVY_PUSH_MIN = 10.0  # contrast list in same themes


def _num(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except (TypeError, ValueError):
        return default


def is_etf_like(s: dict) -> bool:
    code = str(s.get("code") or "")
    name = str(s.get("name") or "")
    if s.get("is_etf"):
        return True
    if "ETF" in name or "槓桿" in name or "反向" in name:
        return True
    if code.startswith("00") and len(code) >= 4:
        return True
    return False


def topic_of(s: dict) -> str:
    t = s.get("topic_label") or s.get("topic") or ""
    if isinstance(t, list):
        t = t[0] if t else ""
    t = str(t).strip()
    if not t or t in {"None", "null", "未对应", "未對應"}:
        return "未對應"
    return t


def inst_net(s: dict) -> float:
    if s.get("inst_net") is not None:
        return _num(s.get("inst_net"))
    return (
        _num(s.get("foreign_net"))
        + _num(s.get("trust_net"))
        + _num(s.get("dealer_net"))
    )


def theme_nets(stocks: list) -> dict[str, float]:
    out: dict[str, float] = {}
    for s in stocks:
        if is_etf_like(s):
            continue
        t = topic_of(s)
        if t == "未對應":
            continue
        out[t] = out.get(t, 0.0) + inst_net(s)
    return out


def rank_themes(nets: dict[str, float], *, top_n: int, side: str) -> list[dict]:
    items = [(k, v) for k, v in nets.items() if abs(v) >= TOPIC_FLOW_MIN_ABS]
    if side == "in":
        items.sort(key=lambda x: x[1], reverse=True)
        items = [x for x in items if x[1] > 0][:top_n]
    else:
        items.sort(key=lambda x: x[1])
        items = [x for x in items if x[1] < 0][:top_n]
    return [{"topic": k, "inst_net": round(v, 3)} for k, v in items]


def regulatory_blocked(s: dict) -> bool:
    if s.get("disposition") or s.get("notice"):
        return True
    if s.get("disp_risk") in {"high", "med"}:
        return True
    if s.get("daytrade_pause") or s.get("daytrade_suspended"):
        return True
    return False


def stock_row(s: dict, *, extra: Optional[dict] = None) -> dict:
    row = {
        "code": s.get("code"),
        "name": s.get("name"),
        "market": s.get("market"),
        "topic": topic_of(s),
        "inst_net": round(inst_net(s), 3),
        "foreign_net": round(_num(s.get("foreign_net")), 3),
        "trust_net": round(_num(s.get("trust_net")), 3),
        "dealer_net": round(_num(s.get("dealer_net")), 3),
        "change": s.get("change"),
        "amount": s.get("amount"),
        "foreign_hold_pct": s.get("foreign_hold_pct"),
        "margin_util": round(_num(s.get("margin_util")), 4),
        "sbl_avail": s.get("sbl_avail"),
        "disposition": bool(s.get("disposition")),
        "notice": bool(s.get("notice")),
        "disp_risk": s.get("disp_risk") or "none",
    }
    if extra:
        row.update(extra)
    return row


def score_mild_push(s: dict, inflow_topics: set[str]) -> Optional[float]:
    """Higher = better mild-push candidate. None = reject."""
    if is_etf_like(s) or regulatory_blocked(s):
        return None
    t = topic_of(s)
    if t not in inflow_topics:
        return None
    n = inst_net(s)
    if n < MILD_PUSH_MIN or n > MILD_PUSH_MAX:
        return None
    # prefer foreign-led mild buy, low margin util, not already extreme foreign hold
    foreign = _num(s.get("foreign_net"))
    margin = _num(s.get("margin_util"))
    fh = s.get("foreign_hold_pct")
    score = n * 10.0
    if foreign > 0:
        score += min(foreign, 5.0) * 2.0
    score -= margin * 20.0  # penalize leverage
    if fh is not None and _num(fh) >= 55:
        score -= 5.0  # already very held — different narrative
    if _num(s.get("trust_net")) > 0 and foreign > 0:
        score += 2.0  # aligned
    return round(score, 3)


def screen_mild_push(stocks: list, inflow: list[dict], noise_set: set | None = None) -> list[dict]:
    topics = {x["topic"] for x in inflow}
    noise_set = noise_set or set()
    scored = []
    for s in stocks:
        sc = score_mild_push(s, topics)
        if sc is None:
            continue
        why = [
            f"流入题材「{topic_of(s)}」",
            f"法人净买温和 {inst_net(s):.2f} 千张（区间 {MILD_PUSH_MIN}–{MILD_PUSH_MAX}）",
            "无注意／处置／逼近处置／当冲暂停旗标",
        ]
        if s.get("code") in noise_set:
            sc = round(sc * 0.5, 3)
            why.append("当冲噪音降权×0.5")
        scored.append(stock_row(s, extra={
            "screen": "mild_push",
            "score": sc,
            "why": why,
        }))
    scored.sort(key=lambda r: r["score"], reverse=True)
    return scored[:40]


def screen_heavy_contrast(stocks: list, inflow: list[dict]) -> list[dict]:
    """Same themes but already heavy institutional buy — not 'light push'."""
    topics = {x["topic"] for x in inflow}
    rows = []
    for s in stocks:
        if is_etf_like(s) or topic_of(s) not in topics:
            continue
        n = inst_net(s)
        if n < HEAVY_PUSH_MIN:
            continue
        rows.append(stock_row(s, extra={
            "screen": "heavy_push",
            "score": round(n, 3),
            "why": [f"同题材大额净买 {n:.2f} 千张（≥{HEAVY_PUSH_MIN}）— 对照用，非轻推"],
        }))
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows[:20]


def exit_reasons(s: dict, outflow_topics: set[str]) -> list[str]:
    reasons = []
    t = topic_of(s)
    n = inst_net(s)
    foreign = _num(s.get("foreign_net"))
    margin = _num(s.get("margin_util"))

    if t in outflow_topics and n <= EXIT_INST_SELL:
        reasons.append(f"流出题材「{t}」+ 法人卖 {n:.2f} 千张")
    if foreign <= EXIT_FOREIGN_SELL and margin >= EXIT_MARGIN_UTIL:
        reasons.append(f"外资卖 {foreign:.2f} + 融资使用率 {margin*100:.1f}%（杠杆接力风险）")
    if s.get("disposition"):
        reasons.append("官方处置中")
    elif s.get("disp_risk") == "high":
        reasons.append(f"逼近处置（disp_risk=high）{s.get('disp_risk_reason') or ''}".strip())
    elif s.get("disp_risk") == "med":
        reasons.append("处置风险 med")
    if s.get("notice") and t in outflow_topics:
        reasons.append("注意股且题材流出")
    return reasons


def score_exit(s: dict, reasons: list[str]) -> float:
    score = 10.0 * len(reasons)
    score -= inst_net(s)  # more negative sell → higher priority
    if any("处置" in r for r in reasons):
        score += 15.0
    if any("杠杆接力" in r for r in reasons):
        score += 8.0
    return round(score, 3)


def screen_exit_watch(stocks: list, outflow: list[dict]) -> list[dict]:
    topics = {x["topic"] for x in outflow}
    rows = []
    for s in stocks:
        if is_etf_like(s):
            continue
        reasons = exit_reasons(s, topics)
        if not reasons:
            continue
        # require material signal
        if len(reasons) == 1 and "处置风险 med" in reasons[0]:
            continue
        rows.append(stock_row(s, extra={
            "screen": "exit_watch",
            "score": score_exit(s, reasons),
            "why": reasons,
        }))
    rows.sort(key=lambda r: r["score"], reverse=True)
    return rows[:50]


def load_regime_for(date: str) -> dict:
    if REGIMES.exists():
        doc = json.loads(REGIMES.read_text(encoding="utf-8"))
        for d in doc.get("days") or []:
            if d.get("date") == date:
                return d
    if REGIME_LATEST.exists():
        d = json.loads(REGIME_LATEST.read_text(encoding="utf-8"))
        if d.get("date") == date:
            return d
    return {}


def build_day(day: dict, hist_theme_nets: list | None = None) -> dict:
    date = (day.get("meta") or {}).get("date") or day.get("date")
    stocks = day.get("stocks") or []
    kpi = day.get("market_kpi") or {}
    nets = theme_nets(stocks)
    inflow = rank_themes(nets, top_n=TOPIC_INFLOW_TOP_N, side="in")
    outflow = rank_themes(nets, top_n=TOPIC_OUTFLOW_TOP_N, side="out")

    noise, hot_tape = sx.screen_daytrade_noise(stocks, kpi, is_etf_like, stock_row)
    noise_set = sx.noise_codes(noise)

    mild = screen_mild_push(stocks, inflow, noise_set)
    heavy = screen_heavy_contrast(stocks, inflow)
    exits = screen_exit_watch(stocks, outflow)

    fsf = sx.screen_foreign_stock_flow(stocks, is_etf_like, stock_row)
    lev = sx.screen_leverage_pressure(stocks, is_etf_like, stock_row)
    short = sx.screen_short_ammo(stocks, is_etf_like, stock_row)
    disp = sx.screen_disposal_countdown(stocks, is_etf_like, stock_row)
    today_themes = sx.theme_nets_from_day(day, topic_of, inst_net, is_etf_like)
    rot = sx.screen_theme_rotation(today_themes, hist_theme_nets or [])
    align = sx.screen_inst_alignment(stocks, is_etf_like, stock_row)
    msplit = sx.market_split(kpi)

    regime = load_regime_for(date)
    return {
        "date": date,
        "generated_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
        "disclaimer": "Deterministic screen from market aggregates — not investment advice / not a prediction.",
        "params": {
            "mild_push_inst_net": [MILD_PUSH_MIN, MILD_PUSH_MAX],
            "unit_inst": "千张",
            "topic_inflow_top_n": TOPIC_INFLOW_TOP_N,
            "topic_outflow_top_n": TOPIC_OUTFLOW_TOP_N,
            "exit_foreign_sell": EXIT_FOREIGN_SELL,
            "exit_margin_util": EXIT_MARGIN_UTIL,
            "heavy_push_min": HEAVY_PUSH_MIN,
            "foreign_hold_high": sx.FH_HIGH,
            "foreign_hold_low": sx.FH_LOW,
            "daytrade_hot_pct": sx.DAYTRADE_HOT,
            "theme_delta": sx.THEME_DELTA,
            "split_abs_yi": sx.SPLIT_ABS,
            "hot_tape": hot_tape,
        },
        "regime": {
            "primary": regime.get("primary"),
            "primary_label": regime.get("primary_label"),
            "secondary": regime.get("secondary"),
            "secondary_label": regime.get("secondary_label"),
            "confidence": regime.get("confidence"),
        },
        "themes_in": inflow,
        "themes_out": outflow,
        "mild_push": mild,
        "heavy_push_contrast": heavy,
        "exit_watch": exits,
        "foreign_stock_flow": fsf,
        "leverage_pressure": lev,
        "short_ammo": short,
        "disposal_countdown": disp,
        "theme_rotation": rot,
        "inst_alignment": align,
        "daytrade_noise": noise,
        "market_split": msplit,
        "counts": {
            "mild_push": len(mild),
            "heavy_push_contrast": len(heavy),
            "exit_watch": len(exits),
            "accumulation": len(fsf["accumulation"]),
            "fresh_money": len(fsf["fresh_money"]),
            "distribution": len(fsf["distribution"]),
            "leverage_trap": len(lev["leverage_trap"]),
            "delever_with_flow": len(lev["delever_with_flow"]),
            "squeeze_risk": len(short["squeeze_risk"]),
            "fuel_for_shorts": len(short["fuel_for_shorts"]),
            "disposal_countdown": len(disp),
            "theme_acceleration": len(rot["theme_acceleration"]),
            "theme_fade": len(rot["theme_fade"]),
            "aligned_bid": len(align["aligned_bid"]),
            "conflict": len(align["conflict"]),
            "daytrade_noise": len(noise),
        },
    }


def build(dates: Optional[list[str]] = None) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    index_path = CURATED_DIR / "index.json"
    if dates is None:
        if index_path.exists():
            dates = json.loads(index_path.read_text(encoding="utf-8"))
        else:
            dates = sorted(p.stem for p in CURATED_DIR.glob("????-??-??.json"))

    written = []
    latest = None
    hist_theme: list = []
    for date in dates:
        path = CURATED_DIR / f"{date}.json"
        if not path.exists():
            continue
        day = json.loads(path.read_text(encoding="utf-8"))
        payload = build_day(day, hist_theme_nets=hist_theme[-3:])
        out = OUT_DIR / f"{date}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        written.append(date)
        latest = payload
        hist_theme.append(sx.theme_nets_from_day(day, topic_of, inst_net, is_etf_like))

    if latest:
        OUT_LATEST.write_text(json.dumps(latest, ensure_ascii=False, indent=2), encoding="utf-8")
    OUT_INDEX.write_text(json.dumps(written, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"dates": written, "latest": latest}



def main():
    result = build()
    latest = result.get("latest") or {}
    print(f"screens → {OUT_DIR} ({len(result['dates'])} days)")
    print(f"latest → {OUT_LATEST} date={latest.get('date')}")
    print("themes_in", latest.get("themes_in"))
    print("themes_out", latest.get("themes_out"))
    print("counts", latest.get("counts"))
    print("mild_push top5:")
    for r in (latest.get("mild_push") or [])[:5]:
        print(f"  {r['code']} {r['name']} score={r['score']} inst={r['inst_net']} | {r['topic']}")
    print("exit_watch top5:")
    for r in (latest.get("exit_watch") or [])[:5]:
        print(f"  {r['code']} {r['name']} score={r['score']} | {'; '.join(r['why'])}")
    print("market_split", latest.get("market_split"))
    print("extra counts", {k: v for k, v in (latest.get("counts") or {}).items() if k not in ("mild_push", "heavy_push_contrast", "exit_watch")})


if __name__ == "__main__":
    main()
