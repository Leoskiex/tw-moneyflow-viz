# AISTOCKMAP / TW money-flow — Local Agent Handoff

**Audience:** a local agent taking over Leoskie’s Taiwan money-flow stack  
**Author context:** Grok Bot agent **AISTOCKMAP** (box + Mac mini + GitHub Pages)  
**Handoff date:** 2026-09-11 (Asia/Taipei; §3 Mac-owns-daily after box crons paused)  
**Latest trade board as-of:** **2026-09-09** screens / **2026-09-11** trade_day (20:45 margin catch-up)

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

## 3. Daily operations — **local Mac owns this** (box crons PAUSED)

> **2026-09-11 user directive:** stop AISTOCKMAP box cron jobs. Daily T86 / FundFlo slim / Pages / 8777 are run by the **local Mac agent**. Do **not** resume box routines unless the user says so.
>
> Ownership tracker: `docs/HANDOVER_OWNERSHIP.md`

### 3.0 Box routines — PAUSED (do not rely on these)

| Was | Routine folder | Status |
|------|----------------|--------|
| 18:30 weekdays | `tw-money-flow-daily-etl` | **PAUSED** |
| 19:00 weekdays | `tw-money-flow-regime-digest` | **PAUSED** |
| 20:45 weekdays | `tw-money-flow-etl-retry-20-45` | **PAUSED** |
| Sun 11:00 | `tw-quarter-backfill` | **PAUSED** |

Suggested local cadence (same times, on Mac): **18:30** primary after T86 (~18:00) · **20:45** margin catch-up · digest paste optional.

### 3.1 Exact Mac commands (canonical daily)

```bash
export TZ=Asia/Taipei
export TW_VIZ_ROOT=/Users/lin/Downloads/tw-moneyflow-viz

# 1) Primary refresh (after T86 ~18:00)
cd /Users/lin/Downloads/twse-trading
python3 refresh_daily.py
# optional force a date: python3 refresh_daily.py 2026-09-11

# 2) Confirm dates align
python3 - <<'PY'
import json
from pathlib import Path
V=Path("/Users/lin/Downloads/tw-moneyflow-viz")
st=json.loads((V/"data/refresh_status.json").read_text())
print("ok", st.get("ok"), "trade_day", st.get("trade_day"))
for name in ["screens_latest.json","regime_latest.json","digest_latest.json"]:
    p=V/"data"/name
    if p.exists():
        d=json.loads(p.read_text())
        print(name, "date", d.get("date") or d.get("asof") or d.get("trade_day"))
PY
# Guardrail: raw/manifest.json latest_trade_day == refresh_status.trade_day
# Prefer screens_latest.date close to trade_day (may lag 1–2d if margin/curated blocked)

# 3) Local UI
/Users/lin/Downloads/twse-trading/bin/ensure_8777.sh
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8777/
# expect 200

# 4) Pages push (from a git clone of Leoskiex/tw-moneyflow-viz)
#    Prefer Mac clone if you keep one; else sync lean files then push.
#    NEVER paste ghp_ into chat — use existing `gh` / `git` auth.
gh auth status   # must be Leoskiex
cd /path/to/tw-moneyflow-viz-git   # e.g. Mac clone OR box /workspace/tw-moneyflow-gh-pages
# Selective add: *_latest.json, regimes, digest, fundflo/latest(+series_top),
# last curated day, html/js, etf/00981a latest — NOT full curated/features/raw
git add …
git -c user.name='Leoskiex' -c user.email='Leoskiex@users.noreply.github.com' \
  commit -m "daily: YYYY-MM-DD refresh"
git push origin main
```

**What `refresh_daily.py` does (order):** fetch trade-day raw (force) → overlays → curated → regimes → screens → 00981A → digest / regime_brief / action_radar → FundFlo slim (`build_fundflo_features`, non-fatal).

Writes: `$TW_VIZ_ROOT/data/refresh_status.json` (`ok`, `trade_day`, per-step status).

### 3.2 Secrets / env (server-only — never in browser or chat)

| Name | Where | Used by | Notes |
|------|--------|---------|--------|
| *(none required for core T86 ETL)* | — | `refresh_daily.py` | TWSE/TPEx public endpoints |
| `TW_VIZ_ROOT` | env | refresh / builders | Mac default: `/Users/lin/Downloads/tw-moneyflow-viz` |
| `FINMIND_TOKEN` | Mac env or local secrets file | `etl/fetch_finmind_candles.py` | **optional / satellite**; not FundFlo daily |
| `FUGLE_API_KEY` | Mac env or local secrets | `etl/fetch_fugle_candles.py` | **optional**; 5m/15m/60m for `stock.html` |
| GitHub | `gh auth login` already on Mac | Pages push | **Never** ask for / print `ghp_` |

Box historically used `/home/box/sand-data/box-secrets.json` `card.*` — local agent should mirror tokens into **Mac env / Keychain / local secrets**, not chat.

### 3.3 CRITICAL BUG FIXED (2026-09-09) — still a daily guardrail

**Symptom:** raw days existed but curated/screens stuck older.

**Cause:** `refresh_daily.py` did not advance `raw/manifest.json` `latest_trade_day`.

**Every refresh verify:**

```text
raw/manifest.json latest_trade_day == refresh_status.trade_day
```

If mismatch → patch manifest and re-run curated/screens builders.

### 3.4 Failure modes (expect these)

| Symptom | Likely cause | What to do |
|---------|--------------|------------|
| **T86 late / empty** ~18:00–18:20 | TWSE not published yet | Wait; re-run 18:30+; do not invent screens |
| **18:30: `MI_MARGN_ALL` / `MI_MARGN_MS` / `TWTASU` fail or nodata** | Margin tables publish later | Expected. Re-run **20:45**. Screens may still advance on T86 |
| **Screens date stuck** (e.g. 09-09 while trade_day 09-11) | Prior day margin `.bad` blocked curated | Fix / re-fetch that day’s MI_MARGN; rebuild curated for gap days; do not fake dates |
| **HTTP 402 / paywall on optional APIs** | FinMind/Fugle plan | Skip satellite candles; core ETL unaffected |
| **Empty / missing FundFlo `series_top.json`** | Slim build skipped or `keep_dates` too small | Re-run `etl/build_fundflo_features.py`; need `keep_dates≥120` for water UI |
| **Copy / sync full pack fails (~2–3GB)** | Size limits | Always **lean** pack: latest overlays + recent curated/screens/etf/fundflo + html/js |
| **`resource_exhausted` on old box cron** | Box quota | Irrelevant now — Mac owns daily; if Mac OOMs, slim data + one day at a time |
| **Pages CDN stale** | jsDelivr / Pages lag | Check `raw.githubusercontent.com/.../digest_latest.json` first; hard-refresh site |

### 3.5 Ship to Mac 8777

```bash
/Users/lin/Downloads/twse-trading/bin/ensure_8777.sh
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8777/
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8777/data/screens_latest.json
```

`ensure_8777.sh` starts `python3 -m http.server 8777 --bind 127.0.0.1` in the viz folder if port free.

### 3.6 Ship to GitHub Pages

Repo: **`Leoskiex/tw-moneyflow-viz`** · site: https://leoskiex.github.io/tw-moneyflow-viz/

#### Auth (HARD RULES)

- Push with already-authenticated `git` / `gh` as **Leoskiex**.
- **NEVER** paste `ghp_` / `gho_` into chat. If missing: user runs `gh auth login` locally.
- Do **not** `git config --global`. One-shot `-c user.name=…` OK.

#### Slim sync include list

- `data/*_latest.json`, `data/regimes.json`, digest md/json
- `data/fundflo/latest.json` + `series_top.json` (required for water UI)
- `data/etf/` / 00981A latest
- last curated day(s), html/js (`index.html`, `fund-flow.html`, `stock.html`, …)
- **Exclude:** `*.gz`, full curated history, features/outcomes bulk, raw dumps

### 3.7 FundFlo shared layer

- Contract: `docs/FUNDFLO_CONTRACT.md`; full history: `docs/FUNDFLO_FULL_HISTORY_HANDBOOK.md`
- Build hooked after curated in `refresh_daily.py` (non-fatal)
- Daily Pages **must** include `data/fundflo/latest.json` (+ `series_top.json`)
- Units: curated `foreign_net` = 千張; FundFlo `*_yi` = 億元 via `foreign_net * price / 100`

### 3.8 Research layer — **optional / out of daily slim**

These are **not** required for the weekday FundFlo / screens / Pages board. Run only when researching:

| Job | Script (under `/Users/lin/Downloads/twse-trading` or box twin) | When |
|-----|----------------------------------------------------------------|------|
| Regime digest paste | `build_daily_digest.py` → `data/digest_latest.json` | Optional after refresh (UI already has digest.html) |
| Action radar | `build_action_radar.py` → consumed by `action-radar.html` | Usually already in refresh; re-run if radar empty |
| Feature Store | `build_feature_store.py` | Research / backfill |
| Lifecycle | `build_lifecycle.py` | Research |
| Outcomes | `build_outcome_engine.py` | Research |
| Theme rotation / fake thrust / signals | `build_theme_rotation.py`, `detect_fake_thrust.py`, `build_strategy_signals.py` | Research |
| Event study / tournament | `event_study.py`, `backtest_strategy_tournament_v1.py` | Research — T+1, no peeking |
| Quarter backfill | `backfill_quarter.py` | Sunday / backlog — **not** daily |

Candles (FinMind daily / Fugle 5m): **satellite** — see `docs/FINMIND_*.md`, `docs/FUGLE_CANDLES.md`. Do **not** put candle fetches inside FundFlo slim.

North-star: `docs/ARCHITECTURE_6LAYER.md`.

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

- Box money-flow crons are **PAUSED** (2026-09-11); local Mac owns daily. Old box `resource_exhausted` is irrelevant unless someone resumes them.
- Pages push must be part of **every** successful local refresh.
- Manifest drift bug — **guardrail required**.
- No proven tradable edge; filters only.
- Two-stage Accum→second_wave strategy **proposed**, not fully tournament-coded as walk-forward-safe book.
- Market-wide ETF creations not built (only 00981A holdings Δ).
- Multi-year threshold sweep for Hard B / breadth Hard not finished.

---

## 8. Playbook for the local agent (checklist)

### A. Weekday “update everything” (Mac — box crons are PAUSED)

1. Mac: `cd /Users/lin/Downloads/twse-trading && TW_VIZ_ROOT=/Users/lin/Downloads/tw-moneyflow-viz python3 refresh_daily.py`
2. Confirm `data/refresh_status.json` `ok=true` and dates align (trade_day / screens / curated / manifest).
3. If gap days: rebuild curated for those dates; rebuild regimes/screens/digest/00981A as needed.
4. `/Users/lin/Downloads/twse-trading/bin/ensure_8777.sh` → `http://127.0.0.1:8777/` = 200.
5. Selective slim sync → git clone of `Leoskiex/tw-moneyflow-viz` → `git push origin main` (existing `gh` auth; never paste tokens).
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

## 錢怎麼流（2026-09-11）
- **全歷史整理手冊（為何只有40天／如何補2023／拉長 series_top）**：`docs/FUNDFLO_FULL_HISTORY_HANDBOOK.md`


- 頁面：`fund-flow.html`（白話「讓水流動」＋泡泡軌跡＋河道摘要）
- 日更 slim 仍須寫 `data/fundflo/series_top.json`，`keep_dates=120`、`top_n=50`（`etl/build_fundflo_features.py`）
- 只有 `latest.json` 時頁面會警告「無法看水流」
- 首頁連結文案：看錢怎麼流

## Handoff status (2026-09-11)
- **日終 FundFlo vs 盤中雷达差距表**：`docs/FUND_FLO_VS_INTRADAY_RADAR.md`


**Local agent owns daily refresh (box crons PAUSED 2026-09-11).** See §3 + `docs/FUNDFLO_FULL_HISTORY_HANDBOOK.md` **rev3** + `docs/HANDOVER_OWNERSHIP.md`. FundFlo UI/active ETF/keep_dates=120 are live; still open: curated index rebuild, screens full-calendar, optional 2023 curate. Always slim-push Pages after a successful refresh.
- **FinMind 整合邊界**：`docs/FINMIND_INTEGRATION.md`（candle 衛星；勿進 FundFlo slim）
