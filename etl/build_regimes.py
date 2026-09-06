#!/usr/bin/env python3
"""
Heuristic market-regime labels from curated day snapshots.

Not ML / not price prediction — readable「体制」tags from flows + rules + topic concentration.
Writes:
  /workspace/tw-moneyflow-viz/data/regimes.json
  /workspace/tw-moneyflow-viz/data/regime_latest.json
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

CURATED_DIR = Path("/workspace/tw-moneyflow-viz/data/curated")
OUT_REGIMES = Path("/workspace/tw-moneyflow-viz/data/regimes.json")
OUT_LATEST = Path("/workspace/tw-moneyflow-viz/data/regime_latest.json")

LABELS = {
    "inst_push": "機構推動",
    "leverage_relay": "槓桿接力",
    "hot_money": "熱錢噪音",
    "risk_off": "風險規避",
    "regulatory": "監管摩擦",
    "mixed": "法人打架",
    "quiet": "平淡",
}

# Thresholds in 億元 (market_kpi) unless noted
FOREIGN_CLEAR = 80.0
FOREIGN_FLAT = 35.0
DOMESTIC_STRONG_OPP = 50.0
MATERIAL = 40.0
MARGIN_POS = 3.0
DAYTRADE_HOT = 40.0
TOP_SHARE_CONC = 0.25
TOP_SHARE_LOW = 0.25
ADVANCE_STRONG_RATIO = 1.15  # advance / max(decline,1)


def _num(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except (TypeError, ValueError):
        return default


def topic_concentration(day: dict) -> dict:
    topics = day.get("topics") or []
    scored = []
    for t in topics:
        net = _num(t.get("inst_net"))
        if net == 0:
            continue
        scored.append({
            "id": t.get("id"),
            "name": t.get("shortname") or t.get("name") or t.get("id") or "—",
            "inst_net": net,
            "abs": abs(net),
        })
    scored.sort(key=lambda r: r["abs"], reverse=True)
    total_abs = sum(r["abs"] for r in scored) or 1.0
    top = scored[0] if scored else None
    top_share = (top["abs"] / total_abs) if top else 0.0
    # fighting: several large topics with mixed signs
    big = [r for r in scored if r["abs"] >= max(8.0, total_abs * 0.08)]
    pos_n = sum(1 for r in big if r["inst_net"] > 0)
    neg_n = sum(1 for r in big if r["inst_net"] < 0)
    fighting = len(big) >= 4 and pos_n >= 2 and neg_n >= 2
    top_buy = next((r for r in scored if r["inst_net"] > 0), None)
    top_buy_share = (top_buy["abs"] / total_abs) if top_buy else 0.0
    return {
        "top_topic": top["name"] if top else None,
        "top_topic_net": round(top["inst_net"], 3) if top else None,
        "top_share": round(top_share, 4),
        "top_buy_topic": top_buy["name"] if top_buy else None,
        "top_buy_net": round(top_buy["inst_net"], 3) if top_buy else None,
        "top_buy_share": round(top_buy_share, 4),
        "fighting": fighting,
        "big_n": len(big),
    }


def _fmt_yi(v: float) -> str:
    return f"{v:+.1f} 億"


def score_regimes(day: dict) -> list[tuple[str, float, list[str]]]:
    """Return list of (id, confidence 0-1, evidence[]) for triggered regimes."""
    kpi = day.get("market_kpi") or {}
    rm = day.get("rules_meta") or {}
    conc = topic_concentration(day)

    foreign = _num(kpi.get("all_foreign_net"), _num(kpi.get("foreign_net")))
    trust = _num(kpi.get("all_trust_net"), _num(kpi.get("trust_net")))
    dealer = _num(kpi.get("all_dealer_net"), _num(kpi.get("dealer_net")))
    daytrade = _num(kpi.get("daytrade_pct"))
    margin_delta = _num(kpi.get("margin_delta"))
    advance = int(_num(kpi.get("advance")))
    decline = int(_num(kpi.get("decline")))

    notice_n = int(_num(rm.get("notice_n")))
    disposition_n = int(_num(rm.get("disposition_n")))
    disp_risk_high_n = int(_num(rm.get("disp_risk_high_n")))

    top_name = conc["top_topic"]
    top_net = conc["top_topic_net"]
    top_share = conc["top_share"]
    fighting = conc["fighting"]

    out: list[tuple[str, float, list[str]]] = []

    # --- regulatory ---
    reg_hit = notice_n >= 20 or disposition_n >= 10 or disp_risk_high_n >= 10
    if reg_hit:
        parts = []
        if notice_n >= 20:
            parts.append(f"注意股 {notice_n} 檔")
        if disposition_n >= 10:
            parts.append(f"處置 {disposition_n} 檔")
        if disp_risk_high_n >= 10:
            parts.append(f"逼近處置(高) {disp_risk_high_n} 檔")
        conf = 0.55
        if disposition_n >= 10:
            conf += 0.15
        if disp_risk_high_n >= 10:
            conf += 0.1
        if notice_n >= 30:
            conf += 0.05
        out.append(("regulatory", min(0.95, conf), ["監管摩擦：" + "、".join(parts)]))

    # --- risk_off ---
    if foreign <= -FOREIGN_CLEAR and advance < decline:
        conf = 0.62
        conf += min(0.25, abs(foreign) / 2000.0)
        if advance < decline * 0.7:
            conf += 0.08
        ev = [
            f"外資全市場淨賣 {_fmt_yi(foreign)}，上漲 {advance}／下跌 {decline}",
        ]
        if margin_delta < 0:
            ev.append(f"融資 Δ {_fmt_yi(margin_delta)}（去槓桿）")
        out.append(("risk_off", min(0.96, conf), ev))

    # --- mixed (法人打架) ---
    foreign_mat = abs(foreign) >= MATERIAL
    trust_opp = foreign_mat and abs(trust) >= MATERIAL and (foreign * trust < 0)
    dealer_opp = foreign_mat and abs(dealer) >= MATERIAL and (foreign * dealer < 0)
    # also trust vs dealer when foreign flat
    trust_dealer_fight = (
        abs(foreign) < FOREIGN_FLAT
        and abs(trust) >= MATERIAL
        and abs(dealer) >= MATERIAL
        and (trust * dealer < 0)
    )
    if trust_opp or dealer_opp or trust_dealer_fight:
        bits = [f"外資 {_fmt_yi(foreign)}", f"投信 {_fmt_yi(trust)}", f"自營 {_fmt_yi(dealer)}"]
        conf = 0.58 + min(0.25, (abs(foreign) + abs(trust) + abs(dealer)) / 2500.0)
        out.append(("mixed", min(0.92, conf), ["法人打架：" + "／".join(bits)]))

    # --- inst_push ---
    strong_opp = (trust <= -DOMESTIC_STRONG_OPP) or (dealer <= -DOMESTIC_STRONG_OPP)
    # allow mild trust sell if dealer helps, or trust near flat
    domestic_ok = not strong_opp or (
        foreign > FOREIGN_CLEAR
        and dealer >= 0
        and trust > -DOMESTIC_STRONG_OPP * 1.2
    )
    # refine: "not strongly opposing" = neither trust nor dealer deeply against foreign
    # If trust is -9 and dealer +64 with foreign +573 → OK
    # If trust -80 and dealer -60 with foreign +200 → not OK
    if foreign >= FOREIGN_CLEAR:
        opp_score = 0.0
        if trust < 0 and foreign > 0:
            opp_score += min(abs(trust), abs(foreign))
        if dealer < 0 and foreign > 0:
            opp_score += min(abs(dealer), abs(foreign))
        not_strongly_opposing = opp_score < DOMESTIC_STRONG_OPP or (
            dealer >= 0 and trust > -DOMESTIC_STRONG_OPP
        )
        buy_name = conc.get("top_buy_topic")
        buy_net = conc.get("top_buy_net")
        buy_share = conc.get("top_buy_share") or 0.0
        concentrated = (
            (buy_share >= TOP_SHARE_CONC)
            or (buy_net is not None and buy_net > 0 and buy_share >= 0.18)
            or (top_net is not None and top_net > 0 and top_share >= TOP_SHARE_CONC)
        )
        if not_strongly_opposing:
            conf = 0.55
            conf += min(0.22, foreign / 1500.0)
            if concentrated:
                conf += 0.12
            if dealer > 0:
                conf += 0.05
            if advance > decline:
                conf += 0.05
            ev = [f"外資全市場淨買 {_fmt_yi(foreign)}（投信 {_fmt_yi(trust)}／自營 {_fmt_yi(dealer)}）"]
            if buy_name and buy_net is not None:
                ev.append(
                    f"題材集中：{buy_name} 法人淨額 {buy_net:+.1f} 千張（佔比 {buy_share*100:.0f}%）"
                )
            elif top_name and top_net is not None and top_net > 0:
                ev.append(
                    f"題材集中：{top_name} 法人淨額 {top_net:+.1f} 千張（佔比 {top_share*100:.0f}%）"
                )
            if advance > decline:
                ev.append(f"漲跌家數偏多：上漲 {advance}／下跌 {decline}")
            out.append(("inst_push", min(0.96, conf), ev))

    # --- leverage_relay ---
    foreign_weak = foreign <= FOREIGN_FLAT  # negative or flat
    if foreign_weak and margin_delta > MARGIN_POS:
        conf = 0.52
        conf += min(0.18, margin_delta / 200.0)
        adv_strong = advance >= decline * ADVANCE_STRONG_RATIO
        if adv_strong:
            conf += 0.12
        if foreign < 0:
            conf += 0.05
        ev = [
            f"外資 {_fmt_yi(foreign)}（偏弱／平），融資 Δ {_fmt_yi(margin_delta)}",
        ]
        if adv_strong:
            ev.append(f"上漲家數偏強：{advance} vs 下跌 {decline}")
        out.append(("leverage_relay", min(0.9, conf), ev))

    # --- hot_money ---
    low_conc = top_share < TOP_SHARE_LOW
    if daytrade >= DAYTRADE_HOT and (low_conc or fighting):
        conf = 0.5 + min(0.2, (daytrade - 40) / 50.0)
        if fighting:
            conf += 0.12
        if low_conc:
            conf += 0.08
        ev = [f"當沖占比 {daytrade:.1f}%"]
        if low_conc:
            ev.append(f"題材分散：第一名佔比僅 {top_share*100:.0f}%")
        if fighting:
            ev.append(f"多題材對打（大致量題材 {conc['big_n']} 個異號）")
        out.append(("hot_money", min(0.9, conf), ev))
    elif daytrade >= DAYTRADE_HOT + 5 and foreign >= FOREIGN_CLEAR:
        # elevated daytrade as soft secondary candidate even with concentration
        conf = 0.42 + min(0.12, (daytrade - 40) / 60.0)
        out.append(("hot_money", conf, [f"當沖偏高 {daytrade:.1f}%（主幹仍可能有題材）"]))

    return out


# Primary preference when confidences are close
PRIMARY_PRIORITY = [
    "risk_off",
    "inst_push",
    "mixed",
    "leverage_relay",
    "hot_money",
    "regulatory",
    "quiet",
]


def pick_primary_secondary(
    scored: list[tuple[str, float, list[str]]]
) -> tuple[Optional[str], Optional[str], float, list[str]]:
    if not scored:
        return "quiet", None, 0.4, ["法人淨額與題材波動偏小，標為平淡"]

    # sort by confidence desc, then priority
    pri = {k: i for i, k in enumerate(PRIMARY_PRIORITY)}

    def sort_key(item: tuple[str, float, list[str]]):
        rid, conf, _ = item
        return (-conf, pri.get(rid, 99))

    ranked = sorted(scored, key=sort_key)
    primary_id, pconf, pev = ranked[0]

    secondary_id = None
    sev: list[str] = []
    for rid, conf, ev in ranked[1:]:
        if rid == primary_id:
            continue
        # regulatory often rides as secondary; hot_money can too
        if conf >= 0.45 or rid == "regulatory":
            secondary_id = rid
            sev = ev
            break

    evidence = list(pev)
    for e in sev:
        if e not in evidence:
            evidence.append(e)
    # keep 2–4 bullets
    evidence = evidence[:4]
    conf = pconf
    if secondary_id:
        conf = min(0.98, conf + 0.03)
    return primary_id, secondary_id, round(conf, 3), evidence


def classify_day(day: dict, date: str) -> dict:
    kpi = day.get("market_kpi") or {}
    rm = day.get("rules_meta") or {}
    conc = topic_concentration(day)

    foreign = _num(kpi.get("all_foreign_net"), _num(kpi.get("foreign_net")))
    trust = _num(kpi.get("all_trust_net"), _num(kpi.get("trust_net")))
    dealer = _num(kpi.get("all_dealer_net"), _num(kpi.get("dealer_net")))

    scored = score_regimes(day)
    # If only regulatory fired, still allow quiet as primary with regulatory secondary
    non_reg = [s for s in scored if s[0] != "regulatory"]
    if not non_reg and scored:
        # small nets → quiet + regulatory secondary
        if abs(foreign) < FOREIGN_FLAT and abs(trust) < FOREIGN_FLAT and abs(dealer) < FOREIGN_FLAT:
            primary, secondary = "quiet", "regulatory"
            conf = 0.45
            evidence = ["法人淨額不大，偏平淡"] + scored[0][2]
        else:
            primary, secondary, conf, evidence = pick_primary_secondary(scored)
    elif not scored:
        primary, secondary, conf, evidence = pick_primary_secondary([])
    else:
        primary, secondary, conf, evidence = pick_primary_secondary(scored)

    # Quiet override: nothing material
    if primary != "quiet":
        pass
    elif abs(foreign) < FOREIGN_FLAT and abs(trust) < 25 and abs(dealer) < 25:
        conf = max(conf, 0.45)

    return {
        "date": date,
        "primary": primary,
        "primary_label": LABELS.get(primary or "", primary),
        "secondary": secondary,
        "secondary_label": LABELS.get(secondary, None) if secondary else None,
        "confidence": conf,
        "evidence": evidence,
        "metrics": {
            "foreign": round(foreign, 2),
            "trust": round(trust, 2),
            "dealer": round(dealer, 2),
            "daytrade_pct": round(_num(kpi.get("daytrade_pct")), 2),
            "margin_delta": round(_num(kpi.get("margin_delta")), 2),
            "advance": int(_num(kpi.get("advance"))),
            "decline": int(_num(kpi.get("decline"))),
            "top_topic": conc["top_topic"],
            "top_topic_net": conc["top_topic_net"],
            "top_share": conc["top_share"],
            "notice_n": int(_num(rm.get("notice_n"))),
            "disposition_n": int(_num(rm.get("disposition_n"))),
            "disp_risk_high_n": int(_num(rm.get("disp_risk_high_n"))),
        },
    }


def build() -> dict:
    files = sorted(
        p for p in CURATED_DIR.glob("*.json")
        if re.match(r"^\d{4}-\d{2}-\d{2}\.json$", p.name)
    )
    days = []
    for p in files:
        date = p.stem
        try:
            day = json.loads(p.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"skip {p.name}: {e}")
            continue
        days.append(classify_day(day, date))

    # newest last
    days.sort(key=lambda d: d["date"])
    tw = timezone(timedelta(hours=8))
    payload = {
        "generated_at": datetime.now(tw).strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "days": days,
    }
    OUT_REGIMES.parent.mkdir(parents=True, exist_ok=True)
    OUT_REGIMES.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    latest = days[-1] if days else {}
    OUT_LATEST.write_text(
        json.dumps(latest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return payload


def main():
    payload = build()
    days = payload["days"]
    print(f"Wrote {len(days)} regimes → {OUT_REGIMES}")
    print(f"Latest → {OUT_LATEST}")
    print("\nLast 5:")
    for d in days[-5:]:
        sec = f" + {d['secondary_label']}" if d.get("secondary") else ""
        print(
            f"  {d['date']}: {d['primary_label']}{sec}  "
            f"conf={d['confidence']}  | {d['evidence'][0] if d['evidence'] else ''}"
        )


if __name__ == "__main__":
    main()

# brief generated via build_regime_brief when run as __main__ after build()
