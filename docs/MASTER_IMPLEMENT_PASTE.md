# Implement paste — WAVE 4 (D4 P3 研究庫刷新採納)

**As of:** 2026-09-17 07:35 TPE · CoS  
**Already YES:** D1–D9 · D3 · D4 P0–P2 (runtime + pushed `8e8c64e`). Do not re-do.  
**This wave:** D4 **P3 only** — research refresh → proposal diff → 採納寫回.  
**Separate track:** freshness/TCC — see `docs/FRESHNESS_RUNBOOK.md` (human/FDA or relocate). Do **not** claim FDA; agents may prep Path A plists only if asked in the same paste’s optional appendix.

Give the coding agent the block below.

```text
Read /Users/lin/Downloads/tw-moneyflow-viz/docs/MASTER_DESIGN_AND_GATES.md (D4 P3)
also PRO_FEATURES_DERIVED.md §3 研究庫 AI, KANSOKU_FEATURES_GAP.md,
etl/candle_server.py (/ask, /research-deep), etl/research_deep.py,
src pages Research.jsx, data/research/*.md.

GO: WAVE 4 — D4 P3 研究庫刷新採納 into SPA :8778 + :8790.
Then STOP and report. Do not vendor kansoku. No Longbridge. No keys in frontend.
No FundFlo slim writes. Box crons paused. Do not re-do P0–P2 / D1–D9 / D3.
Do NOT merge AISTOCKMAP. Do NOT start P4 盲盤／畫布 this wave.
Freshness/TCC/FDA is OUT OF SCOPE unless the optional appendix is explicitly included — default SKIP.

### D4 P3 — 研究庫刷新採納
缺口：对现有 md 刷新 → 提案 diff → 用户採納／拒絕寫回（先整篇，再分节若有時間）.

1) Helper POST :8790/research-refresh
   Body: { code, path? }  # default latest research md for code, or deep md
   Behavior:
   - Read current md from data/research/
   - Pack fresh market context (daily+FundFlo+news+SEPA overlays) like research-deep
   - Local LLM proposes a FULL rewritten md (整篇重刷 first)
   - Write proposal to data/research/proposals/<code>-<ts>.md
     AND a sidecar data/research/proposals/<code>-<ts>.diff.json
     { base_path, proposal_path, summary, sections_changed[], created_at }
   - Return job id + poll (queued→pack→llm→propose→done) same pattern as research-deep
   - LLM down → clear error, no fake proposal

2) Helper POST :8790/research-adopt
   Body: { proposal_id or proposal_path, action: "adopt"|"reject" }
   - adopt: backup current md → data/research/history/<code>-<ts>.md ;
            overwrite target md with proposal; append timeline row
            data/research/timeline/<code>.jsonl
            {ts, action, proposal, base}
   - reject: mark proposal rejected in sidecar; no overwrite
   - Never delete history

3) SPA 研究庫
   - On open doc: buttons 「刷新提案」+ progress
   - When proposal ready: show diff summary (and side-by-side or unified diff if cheap)
   - 「採納」／「拒絕」→ call research-adopt; viewer reloads adopted md
   - Timeline strip: last N adopt/reject events for this code

4) Honesty
   - Proposals must field-cite like deep research; no invented numbers
   - If base md missing → offer create via existing 深度研究, not empty adopt

Acceptance:
- [ ] 2454: one refresh → proposal files exist; UI shows diff/summary
- [ ] 採納 → md updated + history backup + timeline row; 拒絕 → md unchanged
- [ ] tokens 0 (src+dist grep)
- [ ] no kansoku-pro files

### Optional appendix — ONLY if paste says INCLUDE_FRESHNESS_PREP
Prep Path A from docs/FRESHNESS_RUNBOOK.md (plist path rewrites to
~/Library/Application Support/tw-moneyflow/runtime/) but DO NOT rsync huge candles
without user OK; DO NOT claim FDA. Default for this wave: SKIP appendix.

After WAVE 4: reply
YES master D4P3
with URLs, proposal paths, adopt smoke on 2454, token grep count.
If push blocked, leave:
  /Users/lin/Library/Application Support/tw-moneyflow/wave4.bundle
Then STOP.
```

---

## Freshness (human + local) — not a coding-agent “feature” wave

Follow `docs/FRESHNESS_RUNBOOK.md`:
1. Prefer **Path A** relocate runtime → Application Support; re-point 8790 / finmind / fugle launchd.
2. Or **Path B** Full Disk Access for python3 (human click).
3. Reboot checklist §6.

---

## Archive — WAVE 3 (done Mini + push 8e8c64e 2026-09-17)

# Implement paste — WAVE 3 (D3 熱力 + D4 P1 記憶 + D4 P2 深研)

**As of:** 2026-09-17 04:40 TPE · CoS  
**Already YES:** D1 D2 D4P0 · WAVE 2 (D9 D8 D7 + radar/board/digest) on Mini runtime. Do not re-do.  
**This wave:** D3 → D4 P1 → D4 P2. Then STOP and report.  
**Stay apart:** AISTOCKMAP `:8765` map stays linked only — do **not** port the map canvas.  
**Topics:** `data/TW_TOPIC_MEMBERS.json` only (no second industry book).

Give the coding agent the block below.

```text
Read /Users/lin/Downloads/tw-moneyflow-viz/docs/MASTER_DESIGN_AND_GATES.md
also PRO_FEATURES_DERIVED.md (§2 深研, §4 長期記憶), ONE_SITE_PLAN.md,
FUNCTION_DATA_MATRIX.md (F02–F06, screens), TOPIC_TAXONOMY_SOT.md,
data/screens_latest.json, data/fundflo/latest.json, data/TW_TOPIC_MEMBERS.json,
etl/candle_server.py (/ask).

GO: WAVE 3 — D3 台股熱力 → D4 P1 長期記憶 → D4 P2 深度研究 into SPA :8778.
Order: D3 → P1 → P2. Then STOP and report.
Do not vendor kansoku. No Longbridge. No US/SPY heatmap. No Streamlit iframe.
No keys in frontend. No FundFlo slim writes. Box crons paused. 分点 stays blocked.
Do NOT merge AISTOCKMAP :8765 into SPA — 今日 link only.
Topics/groups MUST use data/TW_TOPIC_MEMBERS.json (same book as FundFlo/bubble).
Do not re-do D1/D2/D4P0/D7/D8/D9.

### D3 — 台股熱力 (學交互不抄美股)
學 Kansoku／AISTOCKMAP「點格子進個股、顏色＝強弱／流入」；數據＝FundFlo＋screens＋SoT topics。
1) Surface: 今日 subview 「熱力」 AND/OR route `/heat` (same AppSkeleton).
2) Cells = topics/groups from TW_TOPIC_MEMBERS.json; color from FundFlo
   rolling_5d / momentum (foreign|etf|combined) OR screens_latest themes_in/out.
   Size optional = member count or |flow|.
3) Click cell → list members (codes) → click code → /symbol/:code.
4) Mode toggle aligned with /flow (外資／ETF／綜合) if cheap; else one clear default.
5) Docs note in UI footer or docs/HEATMAP_TW.md: 台＝錢／题材；≠ 美股 SPY 板塊熱力.
Acceptance: :8778/heat (or 今日熱力) non-empty; click → symbol; no SPY/Longbridge; tokens 0.

### D4 P1 — 長期記憶
1) Files: data/memory/user.json + data/memory/symbols/<code>.json (create dirs).
   user: risk_pref, watch_notes, rules (e.g. 禁止亂編).
   symbol: last_takeaway, levels_of_interest, user_notes.
2) SPA 設置: edit user memory + clear; 個股右欄 or 助理: edit/clear this symbol.
3) Helper: /ask (and /p2 if present) MUST inject memory when files exist.
   Never return secrets. Missing memory → empty, still works.
4) Smoke: set one user pref in 設置 → /ask on 2454 cites or reflects it; clear works.
Acceptance: files round-trip; ask payload includes memory; clear empties; tokens 0.

### D4 P2 — 深度研究
1) Helper POST :8790/research-deep {code} → packs daily+FundFlo+news+SEPA overlays
   → local LLM → write data/research/<code>-deep-YYYYMMDD.md
   Fixed 六節: 業務／基本面／技術／催化劑／上下游／自審.
   基本面: label honestly if only FinMind/news (no broker fundamentals API).
   Progress: return job id + poll status OR stream stages (queued→pack→llm→write).
2) SPA: 研究庫 button「深度研究」+ progress UI; open resulting md in research viewer.
3) Field cites required in sections (no invented numbers). LLM down → clear error, no fake md.
Acceptance: 2454 produces md with 6 headings + field cites; UI progress; tokens 0.

### Do not in this wave
P3 research-refresh 採納, P4 盲盤／畫布, Pages 5m, whole-market 5m, FDA/TCC ETL,
freshness/FundFlo T86 restore (separate track). Do not invent second topic map.

After WAVE 3: reply
YES master D3 D4P1 D4P2
with URLs, gate checkboxes, memory file paths, deep md path for 2454.
Also run frontend token grep (src+dist) and report count.
Push only via Mini gh as Leoskiex (never paste PAT). If push blocked, leave:
  /Users/lin/Library/Application Support/tw-moneyflow/wave3.bundle
  (tar of spa src dist vite.config.js package.json — include WAVE2 source if still only on agent box)
Then STOP.
```

---

## Archive — WAVE 2 (done on Mini runtime 2026-09-17)

# Implement paste — WAVE 2 (put loose FundFlo + CMI + watch into :8778)

**As of:** 2026-09-16 23:30 TPE · CoS  
**Already YES:** D1 D2 D4P0 (runtime on Mini). Do not re-do those.  
**This wave:** D9 bubbles → D8 CMI badge → D7 `/watch`. Then radar/board/digest as SPA subviews.  
**Stay apart:** AISTOCKMAP site `:8765` — link from 今日, do **not** port the map into React.

Give the coding agent the block below.

```text
Read /Users/lin/Downloads/tw-moneyflow-viz/docs/MASTER_DESIGN_AND_GATES.md
also ONE_SITE_PLAN.md, FUNCTION_DATA_MATRIX.md F02/F03, NVIDIA_WATCH_PAGE.md,
CMI_CONSUME_HANDOFF.md, TOPIC_TAXONOMY_SOT.md, fund-flow.html (paintBubbles),
js/fundflo_model.js.

GO: WAVE 2 — fold remaining FundFlo visuals + CMI weather + NVIDIA watch into SPA :8778.
Order: D9 → D8 → D7 → (if time) radar/board/digest. Then STOP and report.
Do not vendor kansoku. No Longbridge. No Streamlit iframe. No keys in frontend.
No FundFlo slim writes. Box crons paused. 分点 stays blocked.
Do NOT merge AISTOCKMAP :8765 產業地圖 into the SPA — add a 今日 link only.
Topics/groups MUST use data/TW_TOPIC_MEMBERS.json (same book as FundFlo/bubble).
Do not show CMI sqlite themes as a second industry book.

### D9 — bubble flow (highest visual gap)
Port 四象限泡泡 from fund-flow.html into SPA. Do not iframe the html.
1) Surface: 今日 `/` subview 「盤面」 AND/OR route `/flow` (same AppSkeleton).
2) Same math as fundflo_model.js: WINDOW=5 rolling_5d / momentum / rolling_ret_5d;
   modes foreign|etf|combined|turnover.
3) paintBubbles UX: quadrant, mode toggle, playback if series exists.
   Click bubble → /symbol/:code. Color/size from FundFlo; labels topic/group from SoT.
4) Keep D1 rank table. :8777/fund-flow.html redirect → this SPA view (not empty shell).
Acceptance: living bubbles on :8778; mode switch; click→symbol; tokens 0.

### D8 — CMI 天氣 badge on 今日
Thin badge only. Do not iframe Day Operator HTML. No MCPT/STRATEGY_BOOK/FULLSPEC tables.
1) Read data/cmi/day_operator_latest.json (already copied) OR :8790 GET /cmi/day-operator.
2) Badge on `/`: weather.mode + as_of + headline/action.
3) Click → panel: cash_target, allow_new_entries, foreign_net_yi, adv_ratio, regime.
4) Missing file → empty-state, page still works.
Acceptance: badge as_of matches JSON; no research tables in SPA.

### D7 — NVIDIA `/watch` 觀察
Inspired by nvidiascreener.streamlit.app (Portfolio Tracker), self-built.
1) Seed data/watch/nvidia/holdings.json + timeline.json.
   status: current | partnership | exited. Optional tw_code.
2) AppSkeleton tab 觀察 → /watch.
3) Sidebar filters + sort; timeline; tabs Portfolio | Performance | Sectors | News | 13F History.
4) Quotes via :8790 if FINNHUB_API_KEY else static seed. Never return secrets.
5) tw_code → /symbol/:code; US-only → details drawer.
Acceptance: :8778/watch 200; tab visible; no iframe.

### Also this wave (FundFlo leftovers — same 今日/子頁, not new sites)
- 動作雷達: port action-radar.html into `/` or `/radar` (read same JSON; name click → /symbol/:code).
- 看圖版 board.html → `/board` or 今日 subview.
- 日報 digest.html → link/panel on 今日 (same digest JSON).
- 今日: one outbound link 「產業地圖」→ http://127.0.0.1:8765/ (AISTOCKMAP stays separate).

### Do not in this wave
P1 memory, P2 deep-research, D3 TW heatmap, Pages 5m, whole-market 5m, FDA/TCC daily ETL
(that's a separate freshness track). Do not invent a second topic map.

After WAVE 2: reply
YES master D9 D8 D7
with URLs, which leftovers landed (radar/board/digest), gate checkboxes.
Push only via Mini gh as Leoskiex (never paste PAT). If push blocked, say so and leave a bundle at:
/Users/lin/Library/Application Support/tw-moneyflow/wave2.bundle
Then STOP.
```

---

## Archive — WAVE 1 (done, do not re-run)

D1+D2+D4P0 already YES on Mini 2026-09-16. Old paste kept below for history.


<!-- WAVE1 original in git history / prior paste; WAVE2 is live. -->
