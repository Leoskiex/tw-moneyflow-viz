#!/usr/bin/env python3
"""
Deterministic regime briefing — pure Python templates, no LLM.

Input: one day from regimes.json / regime_latest.json (and optional screens).
Output:
  data/regime_briefs/<date>.json
  data/regime_brief_latest.json

Each brief has structured fields + a ready-to-render `markdown` / `paragraphs` block
so the UI and the 19:00 digest can reuse the same copy every day.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

VIZ = Path("/workspace/tw-moneyflow-viz/data")
REGIME_LATEST = VIZ / "regime_latest.json"
REGIMES = VIZ / "regimes.json"
SCREENS_DIR = VIZ / "screens"
SCREENS_LATEST = VIZ / "screens_latest.json"
OUT_DIR = VIZ / "regime_briefs"
OUT_LATEST = VIZ / "regime_brief_latest.json"

TZ8 = timezone(timedelta(hours=8))

# How-to-read blurb per primary regime (fixed copy, not advice)
READ_GUIDE = {
    "inst_push": "機構資金同向偏多時，優先對照流入題材與 mild_push，勿把單日淨買當隔日保證。",
    "leverage_relay": "融資上來、外資不強時，漲勢更依賴槓桿與情緒，留意融資使用率與 exit_watch。",
    "hot_money": "當沖偏高、題材分散時，短線噪音大，交叉驗證要更嚴，避免追擁擠熱門。",
    "risk_off": "外資明顯淨賣且下跌家數居多，偏防守解讀；減碼清單優先看出清與監管旗標。",
    "regulatory": "注意／處置檔數偏高，流動性與交易限制風險上升，處置倒數名單優先看。",
    "mixed": "外資與本土法人方向打架，主題敘事容易反覆，看共識題材多於單邊追價。",
    "quiet": "淨額偏小、體制不鮮明，適合當「無強信號日」，少做方向性延伸。",
}

SECONDARY_NOTE = {
    "regulatory": "次標籤「監管摩擦」代表限制／警示面升溫，即使主標籤偏多也要降倉位假設。",
    "mixed": "次標籤「法人打架」代表機構內部方向不一致，主題擴散力可能受限。",
    "hot_money": "次標籤「熱錢噪音」代表短線交易佔比偏高，價格波動解讀要打折。",
    "risk_off": "次標籤「風險規避」代表賣壓結構仍在，主升敘事需更多確認。",
    "leverage_relay": "次標籤「槓桿接力」代表融資在補力道，回撤時槓桿殺傷可能放大。",
    "inst_push": "次標籤「機構推動」代表外資側仍有支撐，可與主標籤對照權重。",
    "quiet": "次標籤「平淡」代表次要維度信號弱，以主標籤為主。",
}


def _num(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except (TypeError, ValueError):
        return default


def _signed_yi(v: float) -> str:
    return f"{v:+.1f} 億"


def _signed_qian(v: float) -> str:
    return f"{v:+.1f} 千張"


def _pct(v: float, digits: int = 0) -> str:
    return f"{v * 100:.{digits}f}%"


def _conf_bucket(c: float) -> str:
    if c >= 0.85:
        return "高"
    if c >= 0.6:
        return "中高"
    if c >= 0.4:
        return "中"
    return "低"


def _flow_structure(m: dict) -> str:
    f, t, d = _num(m.get("foreign")), _num(m.get("trust")), _num(m.get("dealer"))
    parts = [f"外資 {_signed_yi(f)}", f"投信 {_signed_yi(t)}", f"自營 {_signed_yi(d)}"]
    # who leads
    abs_map = {"外資": abs(f), "投信": abs(t), "自營": abs(d)}
    leader = max(abs_map, key=abs_map.get)
    lead_v = {"外資": f, "投信": t, "自營": d}[leader]
    direction = "淨買" if lead_v > 0 else "淨賣" if lead_v < 0 else "近乎打平"
    return f"{'／'.join(parts)}。量級上以{leader}{direction}為主。"


def _breadth(m: dict) -> str:
    adv, dec = int(_num(m.get("advance"))), int(_num(m.get("decline")))
    if adv + dec <= 0:
        return "漲跌家數資料不足。"
    ratio = adv / max(dec, 1)
    if ratio >= 1.5:
        tone = "明顯偏多"
    elif ratio >= 1.1:
        tone = "略偏多"
    elif ratio <= 0.67:
        tone = "明顯偏空"
    elif ratio <= 0.9:
        tone = "略偏空"
    else:
        tone = "大致均衡"
    return f"上漲 {adv}／下跌 {dec}（比 {ratio:.2f}），市場寬度{tone}。"


def _topic_line(m: dict) -> str:
    topic = m.get("top_topic") or "—"
    net = _num(m.get("top_topic_net"))
    share = _num(m.get("top_share"))
    if topic == "—" or net == 0:
        return "題材集中度資料不足或法人淨額分散。"
    conc = "高度集中" if share >= 0.25 else ("中度集中" if share >= 0.15 else "偏分散")
    return f"最大 |淨額| 題材「{topic}」法人 {_signed_qian(net)}，占當日題材 |淨額| {_pct(share)}（{conc}）。"


def _reg_line(m: dict) -> str:
    n = int(_num(m.get("notice_n")))
    d = int(_num(m.get("disposition_n")))
    h = int(_num(m.get("disp_risk_high_n")))
    heat = n + d * 2 + h
    if heat >= 40:
        tone = "監管／限制摩擦偏高"
    elif heat >= 20:
        tone = "監管摩擦中等偏高"
    elif heat >= 8:
        tone = "監管摩擦溫和"
    else:
        tone = "監管摩擦偏低"
    return f"注意股 {n}、處置 {d}、逼近處置(高) {h} → {tone}。"


def _leverage_line(m: dict) -> str:
    dt = _num(m.get("daytrade_pct"))
    md = _num(m.get("margin_delta"))
    bits = []
    if dt:
        bits.append(f"當沖比重 {dt:.1f}%")
    bits.append(f"融資餘額Δ {_signed_yi(md)}" if md else "融資Δ 近乎持平")
    extra = ""
    if dt >= 40:
        extra = "；當沖偏熱，短線噪音上升"
    elif md >= 5:
        extra = "；融資明顯增加，槓桿在接力"
    elif md <= -5:
        extra = "；融資收缩，槓桿退潮"
    return "、".join(bits) + extra + "。"


def _screens_snip(date: str) -> Optional[dict]:
    p = SCREENS_DIR / f"{date}.json"
    if not p.exists() and SCREENS_LATEST.exists():
        j = json.loads(SCREENS_LATEST.read_text(encoding="utf-8"))
        if j.get("date") == date:
            return j
        return None
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None


def _screen_cross(screens: Optional[dict]) -> list[str]:
    if not screens:
        return ["當日 screens 尚未生成，略過交叉句。"]
    c = screens.get("counts") or {}
    lines = [
        f"計算篩選：mild_push {c.get('mild_push', 0)} 檔、exit_watch {c.get('exit_watch', 0)} 檔"
        f"（heavy {c.get('heavy_push', c.get('heavy_push_contrast', 0))}）。"
    ]
    mild = (screens.get("mild_push") or [])[:3]
    if mild:
        names = "、".join(f"{x.get('code')}{x.get('name')}" for x in mild)
        lines.append(f"輕推觀察前列：{names}。")
    ex = (screens.get("exit_watch") or [])[:3]
    if ex:
        names = "、".join(f"{x.get('code')}{x.get('name')}" for x in ex)
        lines.append(f"退出觀察前列：{names}。")
    rot = screens.get("theme_rotation") or {}
    acc = (rot.get("theme_acceleration") or [])[:2]
    if acc:
        names = "、".join(x.get("topic") or "" for x in acc)
        lines.append(f"題材加速：{names}。")
    return lines


def brief_from_regime(day: dict, screens: Optional[dict] = None) -> dict:
    """Core pure function: regime day dict → structured brief."""
    m = day.get("metrics") or {}
    primary = day.get("primary") or "quiet"
    secondary = day.get("secondary")
    conf = _num(day.get("confidence"))
    date = day.get("date") or ""

    headline = day.get("primary_label") or primary
    if secondary:
        headline = f"{headline}（次：{day.get('secondary_label') or secondary}）"

    one_liner = (
        f"{date} 體制判定為「{day.get('primary_label') or primary}」"
        f"{('／次「' + (day.get('secondary_label') or secondary) + '」') if secondary else ''}"
        f"，信心 {_pct(conf)}（{_conf_bucket(conf)}）。"
        "此為啟發式標籤，非漲跌預測。"
    )

    sections = [
        {
            "id": "verdict",
            "title": "體制定性",
            "lines": [
                one_liner,
                READ_GUIDE.get(primary, READ_GUIDE["quiet"]),
                *([SECONDARY_NOTE[secondary]] if secondary and secondary in SECONDARY_NOTE else []),
            ],
        },
        {
            "id": "flow",
            "title": "資金結構",
            "lines": [_flow_structure(m), _leverage_line(m)],
        },
        {
            "id": "theme",
            "title": "題材集中",
            "lines": [_topic_line(m)],
        },
        {
            "id": "breadth",
            "title": "市場寬度",
            "lines": [_breadth(m)],
        },
        {
            "id": "regulatory",
            "title": "監管摩擦",
            "lines": [_reg_line(m)],
        },
        {
            "id": "screens",
            "title": "與 Screens 交叉",
            "lines": _screen_cross(screens),
        },
        {
            "id": "disclaimer",
            "title": "讀法邊界",
            "lines": [
                "標籤由當日法人流向、題材集中、漲跌家數、融資／當沖、注意處置檔數等規則拼出。",
                "不構成投資建議；隔日不必追單；請與 mild_push／exit_watch／00981A 權重Δ交叉驗證。",
            ],
        },
    ]

    # Flat bullets for UI (compatible with old evidence list + richer)
    bullets: list[str] = []
    for sec in sections:
        if sec["id"] in ("verdict", "disclaimer"):
            continue
        bullets.extend(sec["lines"])

    paragraphs = []
    for sec in sections:
        body = "".join(sec["lines"]) if sec["id"] != "screens" else "".join(sec["lines"])
        # keep as joined readable block
        paragraphs.append(f"【{sec['title']}】" + "".join(sec["lines"]))

    markdown_lines = [f"## {headline}", "", f"*{one_liner}*", ""]
    for sec in sections:
        markdown_lines.append(f"### {sec['title']}")
        for line in sec["lines"]:
            markdown_lines.append(f"- {line}")
        markdown_lines.append("")

    return {
        "date": date,
        "generated_at": datetime.now(TZ8).isoformat(timespec="seconds"),
        "engine": "build_regime_brief.v1",
        "llm": False,
        "primary": primary,
        "primary_label": day.get("primary_label"),
        "secondary": secondary,
        "secondary_label": day.get("secondary_label"),
        "confidence": conf,
        "confidence_bucket": _conf_bucket(conf),
        "headline": headline,
        "one_liner": one_liner,
        "sections": sections,
        "bullets": bullets,
        "paragraphs": paragraphs,
        "markdown": "\n".join(markdown_lines).strip() + "\n",
        "evidence_raw": day.get("evidence") or [],
        "metrics": m,
        "disclaimer": "啟發式體制講解 · 純函數模板 · 非預測 · 非投資建議",
    }


def build_one(day: dict) -> dict:
    screens = _screens_snip(day.get("date") or "")
    return brief_from_regime(day, screens)


def build(all_days: bool = True) -> dict:
    if REGIMES.exists():
        payload = json.loads(REGIMES.read_text(encoding="utf-8"))
        days = payload.get("days") or []
    elif REGIME_LATEST.exists():
        days = [json.loads(REGIME_LATEST.read_text(encoding="utf-8"))]
    else:
        raise SystemExit("no regime JSON")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    briefs = []
    latest = None
    targets = days if all_days else days[-1:]
    for day in targets:
        b = build_one(day)
        (OUT_DIR / f"{b['date']}.json").write_text(
            json.dumps(b, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        briefs.append({"date": b["date"], "headline": b["headline"], "confidence": b["confidence"]})
        latest = b

    if latest:
        OUT_LATEST.write_text(json.dumps(latest, ensure_ascii=False, indent=2), encoding="utf-8")
        # also attach brief onto regime_latest for convenience
        if REGIME_LATEST.exists():
            rl = json.loads(REGIME_LATEST.read_text(encoding="utf-8"))
            if rl.get("date") == latest.get("date"):
                rl["brief"] = {
                    "one_liner": latest["one_liner"],
                    "headline": latest["headline"],
                    "paragraphs": latest["paragraphs"],
                    "bullets": latest["bullets"],
                    "markdown": latest["markdown"],
                    "engine": latest["engine"],
                }
                REGIME_LATEST.write_text(json.dumps(rl, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"regime briefs → {OUT_DIR} ({len(briefs)} days); latest={latest.get('date') if latest else None}")
    return {"dates": [x["date"] for x in briefs], "latest": latest}


def main() -> None:
    build(all_days=True)


if __name__ == "__main__":
    main()
