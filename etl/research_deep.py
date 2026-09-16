#!/usr/bin/env python3
"""WAVE 3 D4 P2 — 深度研究 runner (self-built, kansoku 六節 inferred, not copied).

Usage: python3 etl/research_deep.py <code>
Packs local data (daily K + FundFlo + news + regime + screens + SEPA facts)
→ local LLM (COCKPIT_LLM_URL) → data/research/<code>-deep-YYYYMMDD.md
Fixed 六節: 業務／基本面／技術／催化劑／上下游／自審.
Every claim must cite a field from the packed data (no invented numbers).
基本面 is labelled honestly: only FinMind/news data available (no broker fundamentals API).

Progress: /tmp/deepresearch_<code>.json {running, phase, activity, started_at, updated_at, error, md}
Phases: queued -> pack -> llm -> write -> done | error.
"""
from __future__ import annotations

import json
import os
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/Users/lin/Downloads/tw-moneyflow-viz")
sys.path.insert(0, str(ROOT / "etl"))
DATA = ROOT / "data"
TZ8 = timezone(timedelta(hours=8))
LLM_URL = os.environ.get("COCKPIT_LLM_URL", "http://192.168.31.151:8888/v1").rstrip("/")

code = (sys.argv[1] if len(sys.argv) > 1 else "2330").strip().zfill(4)
PF = Path(f"/tmp/deepresearch_{code}.json")
started = time.time()


def set_phase(phase: str, activity: str, **extra) -> None:
    st = {"running": True, "code": code, "phase": phase, "activity": activity,
          "started_at": started, "updated_at": time.time()}
    st.update(extra)
    PF.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")


def finish(ok: bool, activity: str, **extra) -> None:
    st = {"running": False, "code": code, "phase": "done" if ok else "error",
          "activity": activity, "started_at": started, "updated_at": time.time()}
    if not ok:
        st["error"] = activity
    st.update(extra)
    PF.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")


def load_json(p):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:
        return None


def sma(a, n):
    out, s = [], 0.0
    for i, v in enumerate(a):
        s += v
        if i >= n:
            s -= a[i - n]
        out.append(s / n if i >= n - 1 else None)
    return out


def pack() -> dict:
    set_phase("pack", "packing daily K + FundFlo + news + regime + screens + SEPA")
    doc = load_json(DATA / "candles" / f"{code}.json") or {}
    daily = (doc.get("daily") or [])[-30:]
    C = [b.get("close") for b in (doc.get("daily") or []) if b.get("close") is not None]
    V = [b.get("volume") or 0 for b in (doc.get("daily") or [])]
    facts = {}
    if C:
        facts["close"] = C[-1]
        facts["ma20"] = round(sma(C, 20)[-1], 2) if len(C) >= 20 else None
        facts["ma50"] = round(sma(C, 50)[-1], 2) if len(C) >= 50 else None
        r20, r50, r120 = [], [], []
        if len(C) > 20:
            r20.append(C[-1] / C[-21] - 1)
        if len(C) > 50:
            r50.append(C[-1] / C[-51] - 1)
        if len(C) > 120:
            r120.append(C[-1] / C[-121] - 1)
        facts["ret_20d_pct"] = round(r20[0] * 100, 2) if r20 else None
        facts["ret_50d_pct"] = round(r50[0] * 100, 2) if r50 else None
        facts["ret_120d_pct"] = round(r120[0] * 100, 2) if r120 else None
        if V and len(V) >= 20:
            m = sma(V, 20)[-1]
            facts["vol_ratio_20"] = round(V[-1] / m, 2) if m else None
    # 0050 relative strength
    bench = load_json(DATA / "candles" / "0050.json") or {}
    BC = [b.get("close") for b in (bench.get("daily") or []) if b.get("close") is not None]
    if C and BC and len(C) > 21 and len(BC) > 21:
        facts["rs_vs_0050_20d_pp"] = round((C[-1] / C[-21] - 1 - (BC[-1] / BC[-21] - 1)) * 100, 2)
    # FundFlo
    ff = load_json(DATA / "fundflo" / "latest.json") or {}
    ffrow = next((s for s in (ff.get("stocks") or []) if s.get("code") == code), None)
    if ffrow:
        facts["fundflo"] = {k: ffrow.get(k) for k in (
            "name", "topic", "group", "foreign_flow_yi", "etf_flow_yi", "combined_flow_yi",
            "rolling_foreign_5d_yi", "rolling_combined_5d_yi", "momentum_foreign_5d_yi",
            "rolling_ret_5d", "close")}
    # news (cached by helper; 6h TTL upstream)
    news = load_json(DATA / "news" / f"{code}.json") or {}
    items = news.get("items") or []
    facts["news_top"] = [{"time": i.get("time"), "title": i.get("title"), "source": i.get("source")}
                         for i in items[:8]]
    # regime + screens
    reg = load_json(DATA / "regime_latest.json") or {}
    facts["regime"] = {"primary": reg.get("primary"), "primary_label": reg.get("primary_label"),
                       "confidence": reg.get("confidence")}
    scr = load_json(DATA / "screens_latest.json") or {}
    hits = []
    for sec in ("mild_push", "heavy_push_contrast", "exit_watch", "disposal_countdown"):
        for r in scr.get(sec) or []:
            if str(r.get("code", "")).zfill(4) == code:
                hits.append({"screen": sec, "inst_net": r.get("inst_net"),
                             "foreign_net": r.get("foreign_net"), "why": (r.get("why") or [])[:2]})
    facts["screens"] = hits
    facts["themes_in"] = scr.get("themes_in") or []
    facts["themes_out"] = scr.get("themes_out") or []
    # SEPA facts (same engine as cockpit_p2 / SEPA rail)
    try:
        import cockpit_p2 as p2
        f2 = p2.compute(code)
        if f2:
            facts["sepa"] = {k: f2.get(k) for k in
                             ("close", "ma20", "ma50", "hist", "rsi14", "vol_ratio",
                              "foreign_flow_yi", "combined_5d_yi", "regime", "n_bars")}
            p = f2["close"]
            facts["scenarios"] = {"bull": round(p * 1.08, 2), "base": round(p, 2), "bear": round(p * 0.93, 2)}
    except Exception as e:  # SEPA optional, do not fail the pack
        facts["sepa_error"] = f"{type(e).__name__}: {e}"
    facts["as_of"] = (doc.get("daily") or [{}])[-1].get("time")
    facts["n_daily"] = len(doc.get("daily") or [])
    return {"code": code, "daily_tail": [
        {k: b.get(k) for k in ("time", "open", "high", "low", "close", "volume")} for b in daily],
        **facts}


def llm_six_section(data: dict) -> str:
    set_phase("llm", "local LLM writing six-section deep research")
    d = json.dumps(data, ensure_ascii=False)
    prompt = (
        "你是台股深度研究員。以下為本機資料包（僅可用這些欄位，嚴禁編造數字；缺資料就直說「無本機資料」）：\n"
        f"{d}\n\n"
        "產出繁體中文 markdown，固定六節（依序用 ## 標題）：\n"
        "## 業務（公司/題材位置：用 fundflo.topic/group、新聞標題，簡述產業位置）\n"
        "## 基本面（誠實標註：本機僅有 FinMind 日K與新聞，無券商基本面 API；只能引用 close/MA/量能/外資，"
        "不得編造財報數字）\n"
        "## 技術（引用 close/ma20/ma50/ret_20d_pct/rsi14/vol_ratio_20/rs_vs_0050_20d_pp 等欄位值下結論）\n"
        "## 催化劑（引用 news_top 標題與日期、regime、themes_in/out）\n"
        "## 上下游（用 fundflo topic/group 與新聞中的鏈條線索；無資料則明說）\n"
        "## 自審（列出本文引用的欄位清單、資料缺口、以及「不可下結論之處」；若 sepa.scenarios 存在可引用 bull/base/bear）\n"
        "每節每句結論必須以「欄位=值」形式引用；資料不足就直說。不要 JSON 包裹，直接回 markdown。"
    )
    payload = {"model": os.environ.get("COCKPIT_LLM_MODEL", "qwen3.8-flash-next"),
               "messages": [{"role": "user", "content": prompt}],
               "max_tokens": 2400, "temperature": 0.3,
               "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(LLM_URL + "/chat/completions",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as resp:
        out = json.loads(resp.read().decode())
    msg = (out.get("choices") or [{}])[0].get("message") or {}
    text = (msg.get("content") or msg.get("reasoning") or "").strip()
    if not text:
        raise RuntimeError("LLM 未回傳內容")
    return text


def main() -> int:
    set_phase("queued", "queued")
    try:
        data = pack()
        if not data.get("as_of"):
            finish(False, "無日K資料（data/candles 缺該代碼），不產出假檔")
            return 1
        text = llm_six_section(data)
        set_phase("write", "writing markdown")
        md = (f"# {code} 深度研究（as_of {data['as_of']}）\n\n"
              f"> 生成: {datetime.now(TZ8).strftime('%Y-%m-%d %H:%M')} TPE · 來源: 本機日K/FundFlo/新聞/市況/SEPA（無券商基本面 API）\n\n"
              + text + "\n")
        (DATA / "research").mkdir(parents=True, exist_ok=True)
        day = datetime.now(TZ8).strftime("%Y%m%d")
        out = DATA / "research" / f"{code}-deep-{day}.md"
        out.write_text(md, encoding="utf-8")
        finish(True, f"written {out.name}", md=out.name, md_path=str(out))
        print("DEEP OK", out)
        return 0
    except Exception as e:
        finish(False, f"LLM/打包失敗 {type(e).__name__}: {e}（未產出假檔）")
        print("DEEP FAIL", type(e).__name__, e)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
