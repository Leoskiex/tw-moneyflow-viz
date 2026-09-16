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
