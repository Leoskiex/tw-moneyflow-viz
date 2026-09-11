# Active ETF adapters + fund-flow UI — Local Agent Handoff

**Audience:** Mac local agent owning daily TW money-flow / site updates  
**From:** 反向破解 (adapters + fund-flow UI collab)  
**As of:** 2026-09-11 21:51 Asia/Taipei  
**Trigger:** AISTOCKMAP box crons paused; local Mac owns daily refresh + Pages / 8777.

**Related (do not duplicate T86 SoT here):**
- Schema / issuer table: [`ACTIVE_ETF_HOLDINGS.md`](./ACTIVE_ETF_HOLDINGS.md)
- FundFlo contract / WINDOW=5: [`FUNDFLO_CONTRACT.md`](./FUNDFLO_CONTRACT.md) — **T86 / foreign_net SoT stays with daily FundFlo lane; this doc does not redefine it**
- Full-tree vs slim Pages: [`FUNDFLO_FULL_HISTORY_HANDBOOK.md`](./FUNDFLO_FULL_HISTORY_HANDBOOK.md) rev2
- Ownership board: [`HANDOVER_OWNERSHIP.md`](./HANDOVER_OWNERSHIP.md)

---

## 0. What this lane owns (and does not)

| Owns | Does **not** own |
|------|------------------|
| Active ETF **registry + fetch adapters** | TWSE T86 / curated foreign SoT |
| Writing `data/etf/<code>/holdings*.json` | Box crons (paused) |
| Feeding `etf_flow_yi` via holdings Δ into FundFlo build | Resuming AISTOCKMAP routines |
| `fund-flow.html` / `js/fundflo_model.js` UI cadence & modes | Changing `keep_dates` back to 40 |
| Adding issuers / backfill (Nomura `SearchDate`) | Sponsor 分點 / Signova radar daily |

00981A（瑤池金母／陳釧瑤）= **成長主題雷達主線**；其它主動檔只補強 `etf_flow_yi`，不搶 00981A 故事權重。

---

## 1. Machines & code locations

| Role | Path |
|------|------|
| Canonical trading tree (box; prefer full raw) | `/workspace/twse-trading/` |
| Viz + data (box) | `/workspace/tw-moneyflow-viz/` |
| GitHub working copy | `/workspace/repos/tw-moneyflow-viz/` → `Leoskiex/tw-moneyflow-viz` `main` |
| Mac slim serve | `~/Downloads/tw-moneyflow-viz/` · `http://127.0.0.1:8777/` |
| Pages | https://leoskiex.github.io/tw-moneyflow-viz/ |

**Mac gotcha:** slim tree often **lacks `etl/` + `raw/`**. Heavy FundFlo rebuild / Nomura multi-day backfill belongs on a **full** tree (box or a Mac checkout that has raw+curated+etl). Slim Mac is for **serving** synced HTML/JSON.

**Env (optional):**
```bash
export TW_VIZ_ROOT=/path/to/tw-moneyflow-viz   # default on box: /workspace/tw-moneyflow-viz
# used by active_etf/common.py for holdings output root
```

**Secrets:** active ETF adapters hit **public issuer HTML/API only** — **no API key / token required** for ezMoney / Nomura / Capital / Taishin fetchers.  
(Do not confuse with FinMind / Fugle candle lanes — those have their own docs.)

---

## 2. Registry (enabled issuers)

Source of truth in code: `active_etf/registry.py` (mirrored under `twse-trading/active_etf/` and `tw-moneyflow-viz/etl/active_etf/`).

| code | issuer | source_kind | key | cadence | notes |
|------|--------|-------------|-----|---------|-------|
| **00981A** | 統一 | `ezmoney` | FundCode=`49YTW` | daily | **主線**；既有多日較完整 |
| 00403A | 統一 | `ezmoney` | `63YTW` | daily | 姊妹檔；常僅現況快照直到日揭累積 |
| 00988A | 統一 | `ezmoney` | `61YTW` | daily | 全球股；equity filter **只留數字台股代碼** |
| 00411A | 統一 | `ezmoney` | `64YTW` | daily | 同上海外濾除 |
| 00980A | 野村 | `nomura_api` | FundID + `SearchDate` | daily | **可回填歷史** |
| 00985A | 野村 | `nomura_api` | 同上 | daily | 可回填 |
| 00999A | 野村 | `nomura_api` | 同上 | daily | 可回填 |
| 00982A | 群益 | `capital_api` | product_id `399` | daily | 多半當日快照 |
| 00992A | 群益 | `capital_api` | product_id `500` | daily | 多半當日快照 |
| 00987A | 台新 | `taishin_html` | SSR 表 | daily? | `meta.todo`：基準日欄位待確認 |

Adapters: `ezmoney.py` / `nomura.py` / `capital.py` / `taishin.py` + `common.py`.

---

## 3. Scripts & daily cadence

### 3.1 CLI (holdings only)

From a tree that has `etl/` **or** `twse-trading` with `sys.path` to adapters:

```bash
# Prefer viz etl if present
cd "$TW_VIZ_ROOT/etl"   # or /workspace/twse-trading
python3 fetch_active_etf_holdings.py --list
python3 fetch_active_etf_holdings.py                  # all enabled
python3 fetch_active_etf_holdings.py --codes 00980A,00985A,00999A
```

- Single-fund failure → warn + continue (`n_fail` in summary); **does not abort** batch.
- Writes:
  - `data/etf/<lowercase_code>/holdings/YYYY-MM-DD.json`
  - `data/etf/<lowercase_code>/holdings_latest.json`

### 3.2 Hooked inside `refresh_daily.py` (order)

After curated / digest, **before** FundFlo build:

1. `fetch_active_etf_holdings.run_batch()` — **non-blocking** (errors recorded in `refresh_status.active_etf_holdings`)
2. `build_fundflo_features` with `write_by_date=False` (slim: `latest.json` + `series_top.json`)

Local Mac daily (intended):

1. After T86 ~18:00 Taipei: run full `refresh_daily.py` on a tree that has **raw + etl**  
2. Optional 20:45 margin catch-up (FundFlo lane — see LOCAL_AGENT_HANDOFF)  
3. Sync outputs to Mac 8777 + push Pages slim set (below)  
4. **Do not** restart box crons unless user says so

### 3.3 Day-lag / Δ rules (critical for `etf_flow`)

| Source | Typical lag / history |
|--------|----------------------|
| **野村** | API `SearchDate` → can backfill ~weeks; daily fetch may land **T or T−1** depending on issuer publish |
| **ezMoney / 群益 / 台新** | Often **current snapshot only** — first day after enable has **no share Δ** |
| **etf_flow_yi** | Needs **≥2 consecutive holdings dates** per ETF; new sisters stay flat until day-2+ |
| **Issuer as-of vs calendar** | JSON `date` is holdings as-of (may differ from run calendar day); FundFlo diffs by that `date` |

Nomura historical backfill example (full tree):

```bash
# loop SearchDate over recent trade days via nomura.fetch_holdings(entry, search_date=...)
# then rebuild FundFlo once (keep_dates=120 defaults in etl)
```

### 3.4 FundFlo consume path (read-only on T86)

`build_fundflo_features.load_etf_share_deltas()` scans `data/etf/*/holdings/*.json`, diffs `share` across consecutive dates, aggregates to `(date, stock_code)` → `etf_flow_yi`（億）.

- **`keep_dates` default = 120** (commit `2f37542`); do **not** re-run an old etl that still hardcodes 40.
- UI `PLAYBACK_DAYS = 30` in `fund-flow.html` (open-window only; series may be 120).

---

## 4. Outputs that Pages / Mac 8777 must serve

### 4.1 Slim set (always sync)

| Path | Why |
|------|-----|
| `fund-flow.html` | 四頁籤：外資｜主動式ETF｜綜合｜成交熱度；rAF 插值；模式說明文 |
| `js/fundflo_model.js` | 客戶端公式／插值 |
| `data/fundflo/latest.json` | 當日切片（含 `etf_flow_yi`） |
| `data/fundflo/series_top.json` | 回放；`meta.keep_dates=120`, `top_n=50` |
| `data/etf/**/holdings_latest.json` | 至少統一四檔；建議含野村三檔 |
| `data/etf/**/holdings/YYYY-MM-DD.json` | 需要多日 Δ 時一併推（Nomura 回填尤其重要） |

**Do not** push full `data/fundflo/by_date/`, full curated, or raw to Pages.

### 4.2 URLs

- Pages: https://leoskiex.github.io/tw-moneyflow-viz/fund-flow.html  
- Mac: http://127.0.0.1:8777/fund-flow.html  

Smoke: 開檔約 30 日回放；切「主動式ETF」泡泡應有非零流向（latest 曾見 ~14 檔非零，隨日揭增減）。

---

## 5. Failure modes & what to do

| Symptom | Likely cause | Action |
|---------|--------------|--------|
| `etf_flow` 幾乎不動／非零很少 | 新檔只有 1 天持股；或 Mac 未同步多日 holdings | 等日揭；野村可 SearchDate 回填後重建 FundFlo |
| `refresh_status.active_etf_holdings` = `err:…` 或 `n_fail>0` | 單一投信 HTML/API 改版／逾時 | 看 fail_codes；其餘檔仍應 OK；修對應 adapter |
| ezMoney 空表 | `DataAsset` 結構變了 | 修 `ezmoney.py` 解析；00981A 優先 |
| 野村空／舊日 | `SearchDate` 尚未公布 | adapter 已試候選日；隔日重跑 |
| 群益／台新只有一天 | 預期行為 | 不硬搶歷史；靠日更 |
| `series_top` 變回 ~40 天 | 用了舊 etl（40 預設） | 確認 `build_fundflo_features._compact_series` 預設 **120** 後重跑 |
| 00411A／00988A 缺海外標的 | **by design** 數字代碼 filter | 勿當 bug |
| Mac 8777 無 etl 卻想重跑 FundFlo | slim tree | 到 full tree 跑，再 slim-sync JSON/HTML |
| Pages 與 8777 不一致 | 只推了一邊 | 同 commit 同步 `fund-flow*` + `data/fundflo/*` + 需要的 `data/etf/**` |

---

## 6. UI cadence (fund-flow)

| Item | Value |
|------|--------|
| Modes | 外資｜主動式ETF｜綜合｜成交熱度 |
| Animation | `requestAnimationFrame` + `interpolateState`（非 setInterval 跳日） |
| Default playback | `PLAYBACK_DAYS=30` |
| Series depth | `series_top` keep_dates=**120** |
| Copy | 各模式軸說明已在 `fund-flow.html` `syncAxisCopy()` |

Optional (CoS-locked, **not** daily ETL): 類股日頻彙總／連續同向 — pure UI on existing `latest`/`series_top` only.

---

## 7. Checklist for local agent (ETF / fund-flow slice)

After daily refresh on full tree:

- [ ] `refresh_status.json` shows `active_etf_holdings.n_ok` ≥ most enabled codes  
- [ ] New `holdings_latest.json` mtimes today for 00981A + sisters + Nomura  
- [ ] `data/fundflo/latest.json` meta date == trade day; spot-check `etf_flow_yi` nonzero count  
- [ ] `series_top.json` `meta.keep_dates == 120`  
- [ ] Sync slim set → Mac 8777 + push Pages  
- [ ] Open fund-flow 主動式ETF 煙測  

---

## 8. Pointers for 反向破解 collab

Still fair game without taking daily ETL:

- New issuer adapters / registry enables  
- Nomura-style historical backfill helpers  
- fund-flow visual polish (explainers, optional sector rollup UI)  

Daily T86 + Pages push + 8777 = **local agent**.

