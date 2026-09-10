# AISTOCKMAP / TW money-flow — Local Agent Handoff

**Audience:** a local agent taking over Leoskie’s Taiwan money-flow stack  
**Author context:** Grok Bot agent **AISTOCKMAP** (box + Mac mini + GitHub Pages)  
**Handoff date:** 2026-09-10 (Asia/Taipei)  
**Latest trade board as-of:** **2026-09-09** (20:45 margin catch-up included)

This document is the end-to-end brief: what the project is, what was built, what worked / failed, how to operate daily, how GitHub Pages is updated, research/backtest results, and what to do next.

---

## 0. One-sentence mission

Turn a daily “what happened” TW institutional money-flow dashboard into a **6-layer strategy research engine**, with kid-clear Traditional Chinese story UI, T+1 fills, and an “吃肉喝汤” (follow big money, don’t chase) philosophy.

---

## 1. Machines & paths

| Role | Where | Path / URL |
|------|--------|------------|
| **ETL + research (canonical)** | Grok Bot shared Linux “box” | `/workspace/twse-trading/` (scripts/raw) · `/workspace/tw-moneyflow-viz/` (UI + data) |
| **Local serve** | Mac mini `lindeMac-mini.local` | `/Users/lin/Downloads/tw-moneyflow-viz/` · `http://127.0.0.1:8777/` |
| **Ensure server** | Mac | `/Users/lin/Downloads/twse-trading/bin/ensure_8777.sh` |
| **Public Pages** | GitHub | Repo `Leoskiex/tw-moneyflow-viz` · https://leoskiex.github.io/tw-moneyflow-viz/ |
| **Pages working copy on box** | box | `/workspace/tw-moneyflow-gh-pages/` (clone of same repo, push `main`) |
| **CMI SYSTEM** | Mac (sibling agent) | `/Users/lin/Downloads/cmi_system_v1_5/` · DB `data/cmi.sqlite3` (read-only for AISTOCKMAP) |
| **CMI overlay CSVs** | box + Mac | box: `/workspace/tw-moneyflow-viz/data/cmi/` · Mac: `/Users/lin/Downloads/cmi_system_v1_5/outputs/` |

**User prefs (do not violate):**
- Story/UI copy: **Traditional Chinese (Taiwan)**, vernacular a five-year-old can follow — **no Chinese–English jargon** on story pages (`second_wave`, `risk_off`, etc. stay in code/ids only).
- Investing frame: 可跟汤／只观察／躲开; prefer confirmation over day-1 chase; T+1 open fills in research.
- GitHub account: **Leoskiex**.

**Hard box gotcha:** avoid `Path.iterdir()` / naive `glob` on huge `raw/` trees (can hang). Prefer `ls` + explicit date loops.

---

## 2. Architecture (6 layers)

North-star doc: `/workspace/tw-moneyflow-viz/docs/ARCHITECTURE_6LAYER.md`

1. **Raw** — TWSE/TPEx daily dumps under `/workspace/twse-trading/raw/{YYYY-MM-DD}/`
2. **Feature Store** — continuous features (flow pressure / z / abnormal)
3. **Lifecycle state machine** — Accumulation → … → Repair (+ transitions)
4. **Outcome Engine** — forward/excess returns vs TAIEX + MAE/MFE; T+1 entry proxy
5. **Event Study** — predicate → N, excess, hit, regime splits
6. **Strategy Engine + scoreboard** — soup / filters / tournament leaderboards

**UI IA:**
- Story home: `index.html` (five chapters)
- Charts: `board.html`
- Mobile shell: `m.html`
- Research / radar: `research.html`, `action-radar.html`
- Digest: built by `build_daily_digest.py` → `data/digest_latest.json`

---

## 3. Daily operations (what runs every weekday)

AISTOCKMAP Grok Bot routines (Asia/Taipei):

| Time | Routine folder | Purpose |
|------|----------------|---------|
| **18:30** | `tw-money-flow-daily-etl` | Primary refresh after T86 (~18:00 ex-block) |
| **19:00** | `tw-money-flow-regime-digest` | Paste digest to user |
| **20:45** | `tw-money-flow-etl-retry-20-45` | Second pass when margin/block tables ready |
| Sunday 11:00 | `tw-quarter-backfill` | Quarterly backfill (optional) |

### 3.1 Core command (box)

```bash
cd /workspace/twse-trading && python3 refresh_daily.py
```

Writes `/workspace/tw-moneyflow-viz/data/refresh_status.json`.

Typical pipeline inside / after refresh:
1. Fetch trade-day raw (T86, MI_INDEX, margins, etc.)
2. Overlays (gap4, rules, TPEx QFIIs, …)
3. `build_curated` → regimes → screens → 00981A → digest / regime_brief / action_radar

### 3.2 CRITICAL BUG FIXED (2026-09-09)

**Symptom:** raw days existed through 09-09 but curated/screens stuck at **2026-09-04**.

**Cause:** `refresh_daily.py` did **not** advance `raw/manifest.json` `latest_trade_day`, so `build_curated` stopped early.

**Fix applied:** patch manifest `latest_trade_day` when fetching newer days; rebuild curated for gap days.  
**Local agent must verify** on every refresh that:

```text
raw/manifest.json latest_trade_day == refresh_status.trade_day == screens_latest.date
```

If mismatch → patch manifest and re-run curated/screens builders.

### 3.3 Margin timing

- **18:30:** often `MI_MARGN_*` / `TWTASU` empty → screens date can still advance on T86, but margin buckets empty; secondary regime may say 监管摩擦.
- **20:45:** margins usually OK → accumulation / fresh_money / distribution / daytrade_noise etc. fill; secondary may flip (e.g. 热钱噪音 on 2026-09-09).

### 3.4 Ship to Mac (8777)

Prefer a **lean** pack (latest JSON + html), not full 2–3GB `data/`:

- Copy curated last few days + `*_latest.json` + html/js to  
  `/Users/lin/Downloads/tw-moneyflow-viz/`
- Run `ensure_8777.sh` → expect `http://127.0.0.1:8777/` = 200

Full curated tarball often hits CopyFromBox size / flaky Mac link limits.

### 3.5 Ship to GitHub Pages

Working tree: `/workspace/tw-moneyflow-gh-pages`

```bash
# Selective sync from /workspace/tw-moneyflow-viz (skip *.gz, full curated, features/outcomes bulk)
# Then:
cd /workspace/tw-moneyflow-gh-pages
git add …  # digest/screens/regimes/etf latest + html
git -c user.name='Leoskiex' -c user.email='Leoskiex@users.noreply.github.com' commit -m "…"
git push origin main
```

**Do not** `git config --global` (policy). One-shot `-c user.name/email` is fine if identity missing.

**CDN lag:** `raw.githubusercontent.com` / jsDelivr update before `leoskiex.github.io` sometimes; hard-refresh Pages.

**Recent Pages commits (examples):**
- `4e51d22` — 20:45 margin catch-up 2026-09-09
- `0bb7f36` — evening ETL 18:53 digest
- `4f0fb8c` — first 2026-09-09 core pack
- `c790170` — 2026-09-07 refresh after stuck period

Evening ETL routines historically synced **Mac** but sometimes **forgot Pages** — local agent should **always push Pages** after a successful refresh (or add it to the routine prompt).

---

## 4. Regime labels (天气 / 体制)

Script: `/workspace/twse-trading/build_regimes.py`  
Outputs: `data/regimes.json`, `data/regime_latest.json`

- Heuristic (not ML): foreign/trust/dealer, breadth, margin, regulatory counts, topic concentration.
- **Backfilled 648 days** 2024-01-02 → 2026-09-04+ (was only ~119 days from 2026-03-17 because regimes weren’t rebuilt after curated expansion).
- **Breadth-panic fix:** if `advance/(advance+decline) < 0.05` and tot≥200 → force `risk_off` even if foreign print is positive (fixes **2025-04-07** tariff gap day tagged `inst_push`).

Overlay panel for CMI / crash rules:

- `data/cmi/regime_overlay_daily.csv` (full)
- `data/cmi/regime_overlay_daily_2026YTD.csv`
- Also: `streak_breadth_daily.csv`, `bank_rotation_daily.csv`

Columns include: `date`, `regime_primary`, `foreign_net_yi`, `adv_ratio`, `margin_delta`, lifecycle shares, rolling foreign_5d_sum, etc.

---

## 5. Research / backtests (what was achieved)

### 5.1 Data scale

- Curated calendar expanded via `curate_range.py` ≈ **648 trading days** (2024-01 → 2026-09), then more days through 2026-09-09.
- Outcomes / features / lifecycle / signals rebuilt on that panel.

### 5.2 Validation (examples)

| Signal | Verdict (648d-ish) |
|--------|-------------------|
| Foreign buy streak ≥3 | **not_a_signal** (near-zero lift) |
| Second wave | **useful_as_filter** (~+3pp hit lift; not edge) |
| Fake thrust as long | **useful_as_avoid** |

Docs: `data/validation/STREAK_VALIDATION.md`, `SECOND_WAVE_VALIDATION.md`

### 5.3 Strategy tournament

Scripts:
- `/workspace/twse-trading/backtest_strategy_tournament_v0.py`
- `/workspace/twse-trading/backtest_strategy_tournament_v1.py` (adds CMI arms + more filters)

Rules (shared):
- Signal known at **T close** → **T+1** entry
- Entry price proxy: next close (outcome engine)
- Primary: **5d excess vs TAIEX**; also 3/10/20d
- Cost: zero in v0/v1 (+ optional 10bp RT note)
- Verdicts: `working_filter` | `working_edge_candidate` | `not_working` | `useful_as_avoid`

Outputs: `data/backtests/strategy_tournament_v1/` (`REPORT.md`, `leaderboard.csv`, `summary.json`, `timing_analysis/`)

**Headline results (do not overclaim):**
- **No `working_edge_candidate`** on this sample.
- Best *filters*: mild_push+leverage_relay (short N), `sw_repair_only`, `sw_no_fake` / soup variants (~+0.27% mean excess 5d).
- Lifecycle “头仓→启动加仓→出货卖” pipeline: **not working** as coded; dist-avoid / early-exit on dist are mild filters only.

### 5.4 Timing analysis (enter late / exit early)

Path: `data/backtests/strategy_tournament_v1/timing_analysis/TIMING_REPORT.md`

- **Enter too late: YES (strong)** — among second_wave with prior Accumulation in 10d (~41%), entering on first Accum beat SW-day by ~**+1.65%** mean excess_5d; lag ~**6.7** sessions. SW is confirmation, not first money.
- **Exit too early: conditional** — soup **mean path peaks ~day 3**, then fades (not “hold past 5d always wins”). Large **MFE−realized** gap inside 5d (~+3.5pp) = left money in-window / no take-profit.
- Dist early-exit overlay sparse & slightly harmful; CMI EXIT/REDUCE overlay tiny help.
- **Do not** buy all Accumulation days (large-N path negative) — only the subset that later becomes second_wave (needs a walk-forward proxy, not peeking).

### 5.5 CMI joint work

Teammate: **CMI SYSTEM** (Grok agent id `de5894bf-7698-4aa3-b91d-7bf0a34a1265`).

CMI score table (`cmi_scores`): decisions BUY / BUY_ON_CONFIRMATION / EXIT / REDUCE / DO_NOT_CHASE / …; states REACCELERATION, BREAKDOWN, etc.  
Score history short for event study (~Jul–Sep 2026); prices in DB longer.

**Tournament (T+1 / 5d):** CMI BUY / entry_ready as **long entry** looked **weak** (lean avoid). Useful as **exit overlay** on soup, not first gun.

**CMI monthly soft_gate YTD (their walk-forward, live CMI from prices):** strong absolute returns but large DD; July 2026 killer month.

**Joint crash overlay (Rules A–E) on soft_gate:**

| Rule idea | Meaning |
|-----------|---------|
| Soft A | 2-of-3 for 2 days: risk_off, adv_ratio&lt;0.35, foreign&lt;−400 → raise cash |
| Hard B | foreign&lt;−1500 **and** adv_ratio&lt;0.15 → ~90–100% cash |
| C | leverage_relay + foreign_5d&lt;0 → forbid adds |
| D | CMI EXIT/BREAKDOWN share elevated (when full-market scores exist) |
| E | Re-entry scale-in after heal |

**Arming:**
- Soft A always-on → whipsaw May/early Jun, clips H1.
- Soft A 3/3 arm → still early (2026-03-31).
- **`arming_hard_only`** (arm only on first Hard B): best 2026YTD style for soft_gate (~+120% / DD −15% / Jul −3% in their table) vs plain soft_gate (+91% / DD −35% / Jul −30%).

**2025-04 tariff bridge:** classic Hard B **never fires** (2025 foreign scale smaller). Need **BREADTH Hard**: `adv_ratio < 0.05` (OR classic Hard B). Arm-on **2025-04-07**.  
`bridge hard_agg` best on 2025-04→2026-09 window in their runs (~+162% / DD −18% vs plain +136% / −35%).  
`hard_only` sticky cash after early arm → ~+17% (insurance only).

Confirm overlays (sell-streak breadth + bank rotation): conservatism knob, ≈ hard_only alpha-wise on 2026YTD.

Reports on Mac under `cmi_system_v1_5/outputs/` (WALKFORWARD / TARIFF_BRIDGE / SOFTGATE_* HTML).

---

## 6. Product / UI achievements

- Mobile `m.html`; story-first `index.html` (5 chapters); charts on `board.html`
- Streaks, TPEx quotes into features, TDCC weekly satellite
- 00981A daily holdings cross with screens/regime
- Plain-Chinese story + HOW_TO updates (incl. tournament / validation notes)
- Public Pages kept roughly in sync with digests/screens (when push remembered)

---

## 7. What “done” looks like vs open work

### Done / usable

- Daily ETL + 20:45 margin retry + digest ping (when box resources OK)
- 648d+ research panel, tournament v1, timing analysis
- Regime backfill + breadth-panic rule
- CMI overlay CSV handoff + agreed **hard_agg / Hard B arming** story
- Mac 8777 + Pages for latest board (2026-09-09)

### Not done / fragile

- Routines can die with **`resource_exhausted`** (seen 2026-09-08) — local agent should be able to run `refresh_daily.py` manually.
- Pages push not always part of routine — **add it**.
- Manifest drift bug — **guardrail required**.
- No proven tradable edge; filters only.
- Two-stage Accum→second_wave strategy **proposed**, not fully tournament-coded as walk-forward-safe book.
- Market-wide ETF creations not built (only 00981A holdings Δ).
- Multi-year threshold sweep for Hard B / breadth Hard not finished.

---

## 8. Playbook for the local agent (checklist)

### A. Morning / anytime “update everything”

1. Box: `python3 /workspace/twse-trading/refresh_daily.py` (or Mac equivalent if you relocate stack).
2. Confirm `refresh_status.json` `ok=true` and dates align (trade_day / screens / curated / manifest).
3. If gap days: rebuild curated for those dates; rebuild regimes/screens/digest/00981A as needed.
4. Lean sync → Mac `tw-moneyflow-viz` + `ensure_8777.sh`.
5. Selective sync → `tw-moneyflow-gh-pages` → commit → `git push origin main`.
6. Verify:  
   - `https://raw.githubusercontent.com/Leoskiex/tw-moneyflow-viz/main/data/digest_latest.json`  
   - then Pages URL (allow CDN lag).
7. Ping user one line: trade_day, screens_date, 00981A, ok, 8777.

### B. After 20:45

Re-run refresh (force) so margins populate; re-ship Mac + Pages; note secondary regime / margin bucket counts if they changed.

### C. Research extension

1. Read `docs/ARCHITECTURE_6LAYER.md` + this handoff.
2. Prefer event study before new detectors.
3. Tournament rules stay T+1 / excess_5d; Chinese verdicts for UI.
4. Coordinate with CMI on soft_gate overlays; don’t mix monthly rank book with T+1 event longs in user copy.
5. Next high-value experiment: **walk-forward Accum→second_wave two-stage** without peeking; keep Hard B + breadth Hard as book overlay.

### D. Talking to CMI

CMI is a separate Grok Bot agent with Mac SQLite. Share CSVs under `outputs/`; never write into `cmi.sqlite3`. Keep crash overlay vs entry signal narratives separate.

---

## 9. Key file index

```
/workspace/twse-trading/
  refresh_daily.py          # daily ETL entry
  build_regimes.py          # weather/regime labels (+ breadth panic)
  build_curated.py / curate_range.py
  build_feature_store.py / build_outcome_engine.py / build_lifecycle.py
  build_screens.py / build_daily_digest.py / build_00981a.py
  build_flow_streaks.py
  backtest_strategy_tournament_v0.py
  backtest_strategy_tournament_v1.py

/workspace/tw-moneyflow-viz/
  index.html board.html m.html research.html action-radar.html
  docs/ARCHITECTURE_6LAYER.md
  docs/LOCAL_AGENT_HANDOFF.md          # this file
  data/refresh_status.json
  data/*_latest.json
  data/curated/{date}.json
  data/cmi/*.csv
  data/backtests/strategy_tournament_v1/
  data/validation/

/workspace/tw-moneyflow-gh-pages/     # push to Leoskiex/tw-moneyflow-viz
```

---

## 10. Narrative timeline (compressed)

1. Built story UI + 6-layer scaffolds; filled data gaps (streaks, TPEx, TDCC, 00981A).
2. Expanded curated ~648d; validated streaks / second_wave; ran soup + strategy tournament (filters, no edge).
3. Timing analysis: second_wave enters late vs Accum; 5d mean peaks day 3; MFE gap.
4. Joined CMI scores into tournament; CMI entry weak short-window; exit overlay mild.
5. Designed Soft A / Hard B overlays for CMI soft_gate; **hard_only arming** for 2026YTD; **breadth Hard** for 2025 tariff; **hard_agg** preferred multi-year default in their WF.
6. Backfilled regimes 2024→now; fixed 2025-04-07 breadth panic label.
7. Ops: daily 18:30/20:45 ETL; fixed manifest stuck-at-09-04; pushed Pages (with occasional misses until asked).

---

## 11. Tone when reporting to Leoskie

- Short Chinese status lines for ETL.
- Don’t claim guaranteed edge.
- Separate “CMI monthly rank book” from “AISTOCKMAP T+1 event study.”
- Story UI: pure 繁中白话.

---

*End of handoff. If relocating off the Grok box, copy `twse-trading` + `tw-moneyflow-viz` data + this doc, preserve Mac 8777 layout, and keep GitHub `Leoskiex/tw-moneyflow-viz` as the public mirror.*
