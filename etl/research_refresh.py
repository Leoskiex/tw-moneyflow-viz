#!/usr/bin/env python3
"""WAVE 4 D4 P3 — 研究庫刷新 runner (self-built; kansoku §3 inferred, not copied).

Usage: python3 etl/research_refresh.py <code> [target.md]
Reads the existing research md (default data/research/<code>.md), packs fresh local
context (p2 facts + FundFlo + news + regime + frozen rows + 長期記憶), asks the local
LLM for a full re-write (same section skeleton, every claim field-cited), and writes:
  data/research/proposals/<code>-<ts>.md          (the proposed new md)
  data/research/proposals/<code>-<ts>.md.diff.json (sidecar: section diff + unified diff)
The target md is NOT touched here — adoption happens via /research-adopt.
Progress: /tmp/researchrefresh_<code>.json  {running, phase, activity, started_at, updated_at, error}
Phases: queued -> pack -> llm -> write -> done | error. LLM down -> error, no fake proposal.
"""
from __future__ import annotations

import difflib
import json
import os
import re
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path("/Users/lin/Downloads/tw-moneyflow-viz")
sys.path.insert(0, str(ROOT / "etl"))
DATA = ROOT / "data"
RESEARCH = DATA / "research"
PROPOSALS = RESEARCH / "proposals"
TZ8 = timezone(timedelta(hours=8))
LLM_URL = os.environ.get("COCKPIT_LLM_URL", "http://192.168.31.151:8888/v1").rstrip("/")

code = (sys.argv[1] if len(sys.argv) > 1 else "2330").strip().zfill(4)
target = sys.argv[2] if len(sys.argv) > 2 else f"{code}.md"
PF = Path(f"/tmp/researchrefresh_{code}.json")
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


def sections(text: str) -> dict:
    """Heading -> (heading line, body text) for a markdown doc."""
    out = {}
    cur = "（文件頭）"
    buf = [cur]
    for line in text.splitlines():
        if re.match(r"^#{1,6}\s", line):
            out[cur] = "\n".join(buf[1:]).strip()
            cur = line.strip()
            buf = [cur]
        else:
            buf.append(line)
    out[cur] = "\n".join(buf[1:]).strip()
    out.pop("（文件頭）", None)
    return out


def main() -> int:
    set_phase("queued", "queued")
    target_path = RESEARCH / target
    if not target_path.exists():
        finish(False, f"尚無研究檔 {target}（先跑 P2／深研再生成）")
        return 1
    old_text = target_path.read_text(encoding="utf-8")

    set_phase("pack", "packing current md + FundFlo + news + regime + SEPA + memory")
    # fresh facts via the same rule engine as /p2 (field-cited, deterministic)
    facts = {}
    try:
        import cockpit_p2 as p2
        f2 = p2.compute(code)
        if f2:
            facts = {k: v for k, v in f2.items()}
    except Exception as e:
        facts["sepa_error"] = f"{type(e).__name__}: {e}"
    # frozen rows (last 3) — context for the re-write
    frozen = []
    jf = DATA / "cockpit" / "cockpit.jsonl"
    if jf.exists():
        for line in jf.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                r = json.loads(line)
            except Exception:
                continue
            if str(r.get("code", "")).zfill(4) == code:
                frozen.append({"as_of": r.get("as_of"), "scenarios": r.get("scenarios"),
                               "weights_pct": r.get("weights_pct")})
    frozen = frozen[-3:]
    # news
    news = load_json(DATA / "news" / f"{code}.json") or {}
    news_top = [{"time": i.get("time"), "title": i.get("title")} for i in (news.get("items") or [])[:8]]
    # regime
    reg = load_json(DATA / "regime_latest.json") or {}
    # memory (P1 layer)
    mem_lines = []
    u = load_json(DATA / "memory" / "user.json")
    s = load_json(DATA / "memory" / "symbols" / f"{code}.json")
    if u and u.get("risk_pref"):
        mem_lines.append(f"risk_pref={u['risk_pref']}")
    for k in ("watch_notes", "rules"):
        v = (u or {}).get(k)
        if isinstance(v, list) and v:
            mem_lines.append(f"{k}={'；'.join(str(x) for x in v)[:200]}")
    if s:
        for k in ("last_takeaway", "levels_of_interest", "user_notes"):
            v = s.get(k)
            if isinstance(v, list) and v:
                mem_lines.append(f"{k}={'；'.join(str(x) for x in v)[:200]}")
            elif isinstance(v, str) and v:
                mem_lines.append(f"{k}={v[:200]}")

    set_phase("llm", "local LLM re-writing the doc (same skeleton, field-cited)")
    fact_s = json.dumps(facts, ensure_ascii=False)
    prompt = (
        "你是台股研究員。對「既有研究檔」做整篇重刷：保留原有 ## 章節骨架（可增補，不可刪核心節），"
        "用最新本機欄位更新每一節。每句結論以「欄位=值」引用；資料不足就直說；嚴禁編造數字；不給投資建議。"
        "直接回 markdown 全文，不要 JSON 包裹、不要解釋。\\n\\n"
        f"[既有研究檔]\\n{old_text}\\n\\n"
        f"[本機最新欄位]\\n{fact_s}\\n\\n"
        f"[近期凍結點評]\\n{json.dumps(frozen, ensure_ascii=False)}\\n\\n"
        f"[新聞 top]\\n{json.dumps(news_top, ensure_ascii=False)}\\n\\n"
        f"[市況]\\n{json.dumps({'primary': reg.get('primary'), 'label': reg.get('primary_label'), 'conf': reg.get('confidence')}, ensure_ascii=False)}"
        + (f"\\n\\n[長期記憶]\\n" + "; ".join(mem_lines) if mem_lines else "")
    )
    payload = {"model": os.environ.get("COCKPIT_LLM_MODEL", "qwen3.8-flash-next"),
               "messages": [{"role": "user", "content": prompt}],
               "max_tokens": 2400, "temperature": 0.3,
               "chat_template_kwargs": {"enable_thinking": False}}
    req = urllib.request.Request(LLM_URL + "/chat/completions",
                                 data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            out = json.loads(resp.read().decode())
        msg = (out.get("choices") or [{}])[0].get("message") or {}
        new_text = (msg.get("content") or msg.get("reasoning") or "").strip()
    except Exception as e:
        finish(False, f"LLM 離線/失敗 {type(e).__name__}: {e}（未產出提案）")
        return 1
    if not new_text or len(new_text) < 200:
        finish(False, "LLM 未回傳有效內容（未產出假提案）")
        return 1

    set_phase("write", "writing proposal + diff sidecar")
    PROPOSALS.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(TZ8).strftime("%Y%m%d-%H%M%S")
    pfile = PROPOSALS / f"{code}-{ts}.md"
    pfile.write_text(new_text, encoding="utf-8")

    # diff sidecar
    old_sec = sections(old_text)
    new_sec = sections(new_text)
    added = [h for h in new_sec if h not in old_sec]
    removed = [h for h in old_sec if h not in new_sec]
    changed = [h for h in old_sec if h in new_sec and old_sec[h] != new_sec[h]]
    unchanged = [h for h in old_sec if h in new_sec and old_sec[h] == new_sec[h]]
    diff_lines = list(difflib.unified_diff(old_text.splitlines(), new_text.splitlines(),
                                           fromfile=target, tofile=f"proposals/{pfile.name}",
                                           lineterm=""))
    sidecar = {
        "code": code, "target": target, "file": pfile.name,
        "created_at": datetime.now(TZ8).isoformat(timespec="seconds"),
        "status": "open", "as_of": facts.get("as_of"),
        "old_size": len(old_text), "new_size": len(new_text),
        "sections": {"added": added, "removed": removed, "changed": changed, "unchanged": unchanged},
        "diff_lines": diff_lines[:400], "diff_truncated": len(diff_lines) > 400,
        "adopted_at": None, "rejected_at": None,
    }
    (PROPOSALS / (pfile.name + ".diff.json")).write_text(
        json.dumps(sidecar, ensure_ascii=False, indent=2), encoding="utf-8")
    finish(True, f"proposal written {pfile.name}", proposal=pfile.name,
           diff=pfile.name + ".diff.json",
           sec_added=len(added), sec_changed=len(changed))
    print("REFRESH OK", pfile)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
