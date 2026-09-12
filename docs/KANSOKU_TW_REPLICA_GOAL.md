# Goal — 復刻 Kansoku 並接上台灣股市

**As of:** 2026-09-12 · CoS Tasks  
**User:** 大量參考他們的 code，復刻能力，資料改接台灣。不是把 `Kansoku.app` 塞進我們 repo。

**Done:** P0 on Mini — `stock.html?code=2330` overlays + Bull/Base/Bear rail; `docs/STOCK_OVERLAYS.md`; FundFlo slim untouched; 8777 200.

---

## North star

A local 8777 cockpit that **behaves like Kansoku** (个股驾驶舱 / SEPA / 盘面复盘 / 句句有据) for **TW names**, using **our** bars and chips.

```text
kansoku packages/core + apps/web   →  read, match behavior
FinMind daily + Fugle 5m/15m/60m  →  TW candles
FundFlo T86 / ETF slim            →  法人／主動 ETF 水
local LLM (later)                 →  追問／凍結預測
```

**Not the star:** Longbridge, their Electron shell, Sparkle, Pro `pro.enc`, US heatmap, SPY RS.

---

## Split: local agent vs us (CoS + bots)

### Local agent (Mac Mini) — build the replica

Work in `/Users/lin/Downloads/tw-moneyflow-viz/`.

1. **Read first** (every phase): https://github.com/kansoku-trade/kansoku  
   `packages/core` (indicators, SEPA/Minervini checks, scenario math), `apps/web` (layout: chart + right rail + tabs).  
   Match their constants and pass/fail rules unless a TW swap is documented (e.g. RS vs **0050** not SPY).  
   Do **not** invent a second formula book. Do **not** `git submodule` or copy their repo into ours.

2. **P1 (next, start now)**  
   - `sepa.html?code=` (or mode on `stock.html`) — 8-check dashboard like their SEPA shot  
   - RS vs 0050 (FinMind daily on 0050 + the name)  
   - MA50/150/200 **or** documented TW 20/60/120 swap  
   - 52w high/low, volume vs 20d, verdict Buy / Watch / Avoid  
   - Drawings: horizontal + trend, persist per code  
   - Right-rail tabs: 環境 / 消息 (FinMind news titles if token in **env**)  
   - Deep-link from FundFlo / index names → `stock.html?code=`  
   - Push `stock.html` + `STOCK_OVERLAYS.md` if `6143b95` still unpushed (`gh` on Mini, no token in chat)

3. **P2**  
   - Local LLM: every sentence cites our fields (close, MA20, HIST, FundFlo `foreign_net_yi`, …)  
   - Frozen predictions sqlite + later hit-rate  
   - Optional launchd: notify if a frozen trigger hits on last Fugle bar  
   - `data/research/{code}.md`

4. **Hard no**  
   Longbridge for 2330; keys in browser/Pages; FundFlo slim writes; box cron resume; decrypt Pro.

**P1 acceptance:** `http://127.0.0.1:8777/sepa.html?code=2330` (or equivalent) shows 8 checks + RS vs 0050; 2330 cockpit still works; `STOCK_OVERLAYS.md` updated with SEPA rules **and** the kansoku source file you matched; no `data/fundflo/*` in the diff.

### Us (CoS Tasks + teammates) — TW link + chase

| Who | Owns |
|---|---|
| **CoS Tasks** | This goal, phase gates, paste briefs, Mac path sync of docs |
| **Local agent** | All UI + local JS/html on the Mini |
| **AISTOCKMAP** | Candle ETL already there (`fetch_finmind_*`, `fetch_fugle_*`); answer if stock.html API contract breaks |
| **FundFlo / 反向破解** | Slim + ETF Δ stay the 法人/ETF source; cockpit **reads**, does not rebuild T86 |
| **CMI SYSTEM** | Still consume-only; later may read frozen hit-rate / overlay CSV (separate wire) |

CoS next (not blocking P1):

- Keep `HANDOVER_OWNERSHIP.md` + this goal current  
- After P1 lands: assign AISTOCKMAP only if candle cache/API needs a change  
- After P2: optional CMI read of predictions — **ask user first**  
- Do not start box work that duplicates Mini `stock.html`

---

## TW connection (the actual 連結)

| Need | Source | Who refreshes |
|---|---|---|
| Daily OHLCV (還原 if we have adj) | FinMind `TaiwanStockPrice` → `data/candles/<code>.json` | Mini env `FINMIND_TOKEN` + existing etl |
| 5m / 15m / 60m | Fugle → `data/candles/<code>_5m.json` etc. | Mini env `FUGLE_API_KEY` |
| 0050 for RS | Same FinMind daily for `0050` | Local agent fetch if missing |
| 法人 / 主動 ETF | `data/fundflo/latest.json` + `data/etf/*/holdings*` | `refresh_daily.py` (already Mac) |
| 消息 titles | FinMind `TaiwanStockNews` | P1/P2 etl, 600/hr |
| 目標價 | news parse → targets table (Signova P2) | later, same token |
| Regime overlay for CMI | not in this replica | separate hook |

Session clock: **TW 09:00–13:30**, not US.

---

## Definition of done (whole 復刻)

- [x] P0 cockpit overlays + scenario rail on 2330  
- [ ] P1 SEPA-TW + drawings + 消息 tab + FundFlo deep-link  
- [ ] P2 句句有据 (local LLM + frozen + score)  
- [ ] 2330 / 0050 / one mid-cap smoke on 8777  
- [ ] Pages slim may include **html/js/docs** for cockpit; never tokens, never full raw  
- [ ] Box crons still paused  

---

## Paste — local agent (P1)

```text
Read /Users/lin/Downloads/tw-moneyflow-viz/docs/KANSOKU_TW_REPLICA_GOAL.md
and KANSOKU_FULL_TW_HANDOFF.md

Goal: 復刻 Kansoku cockpit on TW. P0 is done. Do P1 now.
Open github.com/kansoku-trade/kansoku packages/core + apps/web and MATCH their SEPA/Minervini checks and rail tabs. RS vs 0050 not SPY.
Feeds: FinMind + Fugle + existing FundFlo. No Longbridge. No vendor of their repo.
Ship sepa view + drawings + 消息 titles + STOCK_OVERLAYS.md citations of which kansoku files you matched.
Do not touch data/fundflo/*. Push html/docs with gh on this Mac if 6143b95 still local.
Stop after P1 and report 2330 SEPA verdict + RS vs 0050.
```

## Paste — us / AISTOCKMAP (only if candles break)

```text
TW Kansoku replica P1 is on the Mini (stock.html / sepa).
Do not rewrite the cockpit. Only help if FinMind/Fugle cache contract for data/candles/*.json needs a change.
FundFlo slim and box crons unchanged.
```
