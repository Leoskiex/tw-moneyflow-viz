#!/usr/bin/env python3
"""
Deterministic daily digest markdown — no LLM.

Assembles regime_brief + screens tops + 00981A cross into one copy-ready MD.

Writes:
  data/digests/<date>.md
  data/digests/<date>.json
  data/digest_latest.md
  data/digest_latest.json
"""
from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

VIZ = Path("/workspace/tw-moneyflow-viz/data")
OUT_DIR = VIZ / "digests"
OUT_MD = VIZ / "digest_latest.md"
OUT_JSON = VIZ / "digest_latest.json"
TZ8 = timezone(timedelta(hours=8))


def _load(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _num(x: Any, default: float = 0.0) -> float:
    try:
        if x is None:
            return default
        return float(x)
    except (TypeError, ValueError):
        return default


def _fmt_row(r: dict, kind: str = "screen") -> str:
    code = r.get("code") or ""
    name = r.get("name") or ""
    topic = r.get("topic") or "—"
    if kind == "screen":
        return (
            f"| {code} | {name} | {topic} | "
            f"{_num(r.get('inst_net')):+.1f} | {_num(r.get('score')):.1f} |"
        )
    if kind == "flow":
        return (
            f"| {r.get('action') or r.get('dir') or '—'} | {code} | {name} | "
            f"{_num(r.get('weight_pct')):.2f} | {_num(r.get('weight_delta')):+.2f} | "
            f"{int(_num(r.get('share_delta'))):+,} |"
        )
    if kind == "cross":
        return (
            f"| {r.get('bucket') or '—'} | {code} | {name} | {topic} | "
            f"{_num(r.get('weight_pct')):.2f} |"
        )
    return f"| {code} | {name} |"


def resolve_date(prefer: Optional[str] = None) -> str:
    if prefer:
        return prefer
    for p in (
        VIZ / "regime_brief_latest.json",
        VIZ / "screens_latest.json",
        VIZ / "regime_latest.json",
    ):
        j = _load(p)
        if j and j.get("date"):
            return str(j["date"])
    return datetime.now(TZ8).date().isoformat()


def assemble(date: Optional[str] = None) -> dict[str, Any]:
    date = resolve_date(date)
    brief = _load(VIZ / "regime_briefs" / f"{date}.json") or _load(VIZ / "regime_brief_latest.json")
    screens = _load(VIZ / "screens" / f"{date}.json") or _load(VIZ / "screens_latest.json")
    etf = _load(VIZ / "etf" / "00981a" / f"{date}.json") or _load(VIZ / "etf" / "00981a" / "latest.json")
    regime = _load(VIZ / "regime_latest.json")

    # Prefer matching dates; if mismatch, note it
    notes = []
    for label, doc in (("brief", brief), ("screens", screens), ("etf", etf)):
        if doc and doc.get("date") and doc["date"] != date:
            notes.append(f"{label} 日期 {doc['date']} ≠ {date}")

    lines: list[str] = []
    lines.append(f"# 台股資金制式日報 {date}")
    lines.append("")
    lines.append("> 純函數組裝 · 非 LLM · 啟發式標籤 · 非投資建議")
    lines.append(f">")
    lines.append(f"> 生成時間（台北）{datetime.now(TZ8).strftime('%Y-%m-%d %H:%M:%S')} · engine `build_daily_digest.v1`")
    if notes:
        lines.append(">")
        lines.append("> 注意：" + "；".join(notes))
    lines.append("")

    # --- Regime brief ---
    lines.append("## 1. 資金體制制式講解")
    lines.append("")
    if brief:
        lines.append(f"**{brief.get('headline') or '—'}**")
        lines.append("")
        lines.append(brief.get("one_liner") or "")
        lines.append("")
        for para in brief.get("paragraphs") or []:
            lines.append(para)
            lines.append("")
        if brief.get("disclaimer"):
            lines.append(f"*{brief['disclaimer']}*")
            lines.append("")
    elif regime:
        lines.append(
            f"- 主：{regime.get('primary_label')}／次：{regime.get('secondary_label')} "
            f"信心 {int(_num(regime.get('confidence')) * 100)}%"
        )
        for e in (regime.get("evidence") or [])[:4]:
            lines.append(f"- {e}")
        lines.append("")
        lines.append("_regime_brief 未生成，已退回 evidence_")
        lines.append("")
    else:
        lines.append("_無 regime／brief 資料_")
        lines.append("")

    # --- Screens ---
    lines.append("## 2. Screens 摘要")
    lines.append("")
    if screens:
        c = screens.get("counts") or {}
        lines.append(
            f"- mild_push **{c.get('mild_push', 0)}** · exit_watch **{c.get('exit_watch', 0)}** · "
            f"heavy **{c.get('heavy_push_contrast', c.get('heavy_push', 0))}** · "
            f"fresh **{c.get('fresh_money', 0)}** · trap **{c.get('leverage_trap', 0)}**"
        )
        ms = screens.get("market_split") or {}
        if ms:
            lines.append(f"- market_split：{ms.get('label') or '—'} — {ms.get('why') or ''}")
        themes_in = screens.get("themes_in") or []
        themes_out = screens.get("themes_out") or []
        if themes_in:
            tin = ", ".join(
                (t.get("topic") if isinstance(t, dict) else str(t)) for t in themes_in[:3]
            )
            lines.append(f"- themes_in：{tin}")
        if themes_out:
            tout = ", ".join(
                (t.get("topic") if isinstance(t, dict) else str(t)) for t in themes_out[:3]
            )
            lines.append(f"- themes_out：{tout}")
        rot = screens.get("theme_rotation") or {}
        acc = rot.get("theme_acceleration") or []
        fade = rot.get("theme_fade") or []
        if acc:
            lines.append(
                "- 題材加速："
                + "、".join(f"{x.get('topic')}(Δ{_num(x.get('delta')):+.1f})" for x in acc[:3])
            )
        if fade:
            lines.append(
                "- 題材褪色："
                + "、".join(f"{x.get('topic')}(Δ{_num(x.get('delta')):+.1f})" for x in fade[:3])
            )
        lines.append("")
        lines.append("### mild_push Top 5")
        lines.append("")
        lines.append("| 代碼 | 名稱 | 題材 | 法人 | 分 |")
        lines.append("|---|---|---|---:|---:|")
        for r in (screens.get("mild_push") or [])[:5]:
            lines.append(_fmt_row(r))
        lines.append("")
        lines.append("### exit_watch Top 5")
        lines.append("")
        lines.append("| 代碼 | 名稱 | 題材 | 法人 | 分 |")
        lines.append("|---|---|---|---:|---:|")
        for r in (screens.get("exit_watch") or [])[:5]:
            lines.append(_fmt_row(r))
        lines.append("")
        fsf = screens.get("foreign_stock_flow") or {}
        lines.append("### 外資 fresh / distribution Top 3")
        lines.append("")
        for bucket, key in (("fresh_money", "fresh"), ("distribution", "dist")):
            rows = (fsf.get(bucket) or [])[:3]
            if rows:
                lines.append(f"- **{key}**：" + "、".join(f"{x.get('code')}{x.get('name')}" for x in rows))
        lev = screens.get("leverage_pressure") or {}
        traps = (lev.get("leverage_trap") or [])[:3]
        if traps:
            lines.append(
                "- **leverage_trap**："
                + "、".join(f"{x.get('code')}{x.get('name')}" for x in traps)
            )
        sh = screens.get("short_ammo") or {}
        sq = (sh.get("squeeze_risk") or [])[:3]
        if sq:
            lines.append(
                "- **squeeze_risk**：" + "、".join(f"{x.get('code')}{x.get('name')}" for x in sq)
            )
        disp = [
            x
            for x in (screens.get("disposal_countdown") or [])
            if _num(x.get("countdown"), 99) <= 1
        ][:5]
        if disp:
            lines.append(
                "- **處置倒數≤1**："
                + "、".join(f"{x.get('code')}{x.get('name')}(CD{x.get('countdown')})" for x in disp)
            )
        lines.append("")
        if screens.get("disclaimer"):
            lines.append(f"*{screens['disclaimer']}*")
            lines.append("")
    else:
        lines.append("_無 screens 資料_")
        lines.append("")

    # --- 00981A ---
    lines.append("## 3. 00981A 日揭 × Screens")
    lines.append("")
    if etf:
        mf = etf.get("manager_flow") or {}
        c = mf.get("counts") or {}
        lines.append(
            f"- 資料日 **{etf.get('date')}** · Δ來源 `{mf.get('source') or '—'}`"
            + (f" vs {mf.get('prev_date')}" if mf.get("prev_date") else "")
        )
        lines.append(
            f"- 加碼 {c.get('adds', 0)} · 減碼 {c.get('cuts', 0)} · 新建倉 {c.get('new', 0)} · 出清 {c.get('exits', 0)}"
        )
        if mf.get("note"):
            lines.append(f"- 註：{mf['note']}")
        lines.append("")
        lines.append("### 加減碼 Top")
        lines.append("")
        lines.append("| 向 | 代碼 | 名稱 | 權重% | Δ權重 | Δ股數 |")
        lines.append("|---|---|---|---:|---:|---:|")
        for r in (mf.get("adds") or [])[:3]:
            r = dict(r)
            r["action"] = "加"
            lines.append(_fmt_row(r, "flow"))
        for r in (mf.get("cuts") or [])[:3]:
            r = dict(r)
            r["action"] = "減"
            lines.append(_fmt_row(r, "flow"))
        lines.append("")
        cx = etf.get("cross") or {}
        lines.append("### 交叉桶")
        lines.append("")
        lines.append("| 桶 | 代碼 | 名稱 | 題材 | 權重% |")
        lines.append("|---|---|---|---|---:|")
        for bucket, key in (
            ("intersect_mild_push", "mild"),
            ("intersect_theme_accel", "accel"),
            ("flag_exit_watch", "exit"),
            ("aligned_with_regime", "regime"),
        ):
            for r in (cx.get(bucket) or [])[:5]:
                r = dict(r)
                r["bucket"] = key
                lines.append(_fmt_row(r, "cross"))
        lines.append("")
        if etf.get("disclaimer"):
            lines.append(f"*{etf['disclaimer']}*")
            lines.append("")
    else:
        lines.append("_無 00981A 資料_")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("本檔由 `build_daily_digest.py` 自 JSON 組裝，可直接複製。日更 ETL 後自動刷新。")
    lines.append("")

    md = "\n".join(lines)
    payload = {
        "date": date,
        "generated_at": datetime.now(TZ8).isoformat(timespec="seconds"),
        "engine": "build_daily_digest.v1",
        "llm": False,
        "markdown": md,
        "sources": {
            "brief": bool(brief),
            "screens": bool(screens),
            "etf_00981a": bool(etf),
            "notes": notes,
        },
        "headline": (brief or {}).get("headline") or (regime or {}).get("primary_label"),
        "one_liner": (brief or {}).get("one_liner"),
    }
    return payload


def build(date: Optional[str] = None) -> dict:
    payload = assemble(date)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    d = payload["date"]
    (OUT_DIR / f"{d}.md").write_text(payload["markdown"], encoding="utf-8")
    (OUT_DIR / f"{d}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    OUT_MD.write_text(payload["markdown"], encoding="utf-8")
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"digest → {OUT_MD} date={d} chars={len(payload['markdown'])}")
    return payload


def main() -> None:
    build()


if __name__ == "__main__":
    main()
