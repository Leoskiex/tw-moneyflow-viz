# Local agent handoff — full Kansoku-class cockpit on TW

**Audience:** Mac local agent  
**From:** CoS Tasks · 2026-09-12  
**User intent:** “I want to be able to do **all that**” (README + the three screens: 个股驾驶舱, SEPA 仪表盘, 盘面/复盘).  
**Reference (read only):** https://github.com/kansoku-trade/kansoku  
**Supersedes** the P0-only `KANSOKU_LOCAL_HANDOFF.md` for scope. That file’s host/wrapper notes are still true.

---

## 0. Two tracks (do not mix feeds)

| Track | How you get “all that” | Feed |
|---|---|---|
| **A. Install their app** | This weekend, 1:1 for **US/HK/A only** | Longbridge (required by *their* app) |
| **B. Our TW cockpit** | Rebuild the same *capabilities* on 8777 | **FinMind daily + Fugle 5m/15m/60m + FundFlo T86** |

Track A does **not** give 2330. Track B is the job below.  
Still **do not vendor**: do not copy their Electron repo into `tw-moneyflow-viz`, do not ship `Kansoku.app` as our product, do not decrypt `pro.enc`. Reimplement UI + math. Personal use of their dmg (track A) is fine and separate.

---

## 1. Capability map (README → our system)

Legend: **P0** this sprint · **P1** next · **P2** after LLM/archive works · **A** = use their installed app for US · **skip** = not TW / not ours

| Kansoku thing (from README / shots) | TW equivalent | Phase |
|---|---|---|
| Multi-TF K (5m/15m/1h) live while open | Fugle 5m/15m/60m cache + poll; daily = FinMind | **P0** (partially exists on `stock.html`) |
| MA / MACD on chart | Local JS on our OHLC | **P0** |
| RSI, S1/S2, optional KD/布林 | Local JS | **P0** |
| 形态标注 + 入场/止损/目标价线 | Rule marks from local math; 目标价 from our news→targets P2 | **P1** |
| 画线 (趋势/水平/矩形/斐波那契) | Lightweight Charts primitive + save JSON per code | **P1** |
| AI 画紫色虚线 / 只清 AI 线 | After local LLM; store `source=ai` on drawings | **P2** |
| Bull/Base/Bear 三档 = 100% + 触发条件 | Right rail; **rule-based first**, then local LLM | **P0 stub → P2 live** |
| 预测冻结、不许改口、命中率记分 | Local sqlite: `predictions` + score vs later close | **P2** |
| 关掉图还在巡检 + 通知 | Mac launchd watcher on Fugle last bar (not box cron) | **P2** |
| 右栏：预测 / 环境 / 消息 / 复盘 / AI 点评 | Tabs on `stock.html`; 消息 = FinMind news titles | **P1** |
| 追问「凭什么」+ tool-call 留痕 | Local LLM; log prompts + which bars/overlays were read | **P2** |
| 研究库 + 改稿采纳/拒绝 | `data/research/{code}.md` + simple editor | **P2** |
| 模型分槽、key 进本地 sqlite | Mac env / Keychain; **never** browser, **never** Pages | **P2** |
| SEPA / Minervini 8 勾 + Buy/Watch/Avoid | Same 8 checks; **RS vs 0050** (not SPY); volume vs 20d | **P1** |
| 长期均线价值区 / 成交密集区 / 52w 高低 | Local from FinMind daily | **P1** |
| 盘面看板 + 持仓/资金 | `index.html` / FundFlo + CMI overlay; do not clone US heatmap | **P1** (we already have 法人水) |
| 事件日历 | FinMind / MOPS 法说·除权息 dates (titles only at first) | **P1** |
| ⌘T 标签 / ⌘K / Sparkle / 夜盘推送 | Skip Electron chrome; 8777 + existing launchd | **skip** |
| 多市场 US/HK/A session clock | Track **A** only | **A** |
| Longbridge 账户/资金流/盘口 | **skip** — Fugle+FinMind+T86 | **skip** |
| FRED / SEC / GDELT skills | Optional later USA desk, not TW P0 | **A / later** |
| Pro encrypted features | **skip** | **skip** |

---

## 2. Hard rules

1. TW bars: FinMind daily, Fugle intraday. Token/key **server/Mac env only**.  
2. 法人 / ETF 水: existing FundFlo slim. Do not invent a Longbridge 资金流 for TW.  
3. Do not write radar/kansoku artifacts into `data/fundflo/*` day push.  
4. Box money-flow crons stay **paused**.  
5. Traditional Chinese UI on story pages; code ids can stay English.  
6. Evidence rule (copy their discipline, our data): every AI sentence cites a field (close, MA20, FundFlo foreign_net_yi, …). Frozen predictions are append-only.

---

## 3. Suggested tree (our repo, not theirs)

```text
tw-moneyflow-viz/
  stock.html                 # cockpit (shot 1)
  sepa.html                  # SEPA-TW (shot 2)  or a mode on stock.html
  js/overlays.js             # MA MACD RSI pivots SEPA checks
  js/scenarios.js            # Bull/Base/Bear stub → later LLM
  etl/fetch_finmind_candles.py
  etl/fetch_fugle_candles.py
  data/candles/
  data/research/{code}.md    # P2
  data/cockpit/cockpit.sqlite3   # P2 predictions / hit rate
  docs/STOCK_OVERLAYS.md
  docs/KANSOKU_FULL_TW_HANDOFF.md
```

Serve on `http://127.0.0.1:8777/` (launchd already running).

---

## 4. Build order for the local agent

### P0 — cockpit chart (this week)

- `stock.html?code=2330`: daily + 5m/15m/60m, MA5/20/60, MACD(12,26,9), RSI(14), S1/S2  
- Right rail: three scenario cards (can be empty rules: e.g. MA align / CCI / 距MA20) summing to 100%  
- `docs/STOCK_OVERLAYS.md` with constants  
- Smoke on 8777; DevTools shows **no** tokens  

### P1 — SEPA-TW + 盘面 hook

- New `sepa.html?code=2330` matching shot 2 layout: 8 checks, RS vs **0050**, 52w, MA50/150/200 (or TW 20/60/120 if you document the swap), volume vs 20d, verdict Buy / Watch / Avoid  
- Tabs 环境/消息: FinMind news titles if token present  
- Deep-link from FundFlo / `index.html` name → `stock.html?code=`  
- Drawings: horizontal + trendline persist in `localStorage` or `data/research/{code}.drawings.json`  

### P2 — “句句有据”

- Local LLM (Ollama or Cursor local) reads last N bars + overlay JSON + last FundFlo row  
- Archive prediction to sqlite; later session scores vs next close / 5d  
- Optional launchd: if last 5m bar breaks a frozen trigger, macOS notification  
- Research markdown editor  

### Track A (optional, same week, not blocking P0)

- Install `Kansoku-*-arm64.dmg`, right-click Open, Longbridge login  
- Use only for US/HK/A. Do not expect 2330.

---

## 5. Acceptance (P0)

- [ ] 2330 daily + 5m overlays visible on 8777  
- [ ] Bull/Base/Bear rail renders (rules OK)  
- [ ] `STOCK_OVERLAYS.md` written  
- [ ] No FundFlo slim in the diff  
- [ ] Report last daily close + MA20 + MACD histogram for 2330  

P1/P2 each get their own report when you start them.

---

## 6. Copy-paste brief

```text
Read /Users/lin/Downloads/tw-moneyflow-viz/docs/KANSOKU_FULL_TW_HANDOFF.md

User wants the full Kansoku cockpit on TW, not a vendor of their app.
Feeds: FinMind daily + Fugle 5m/15m/60m + existing FundFlo. No Longbridge on TW.
Do P0 first: stock.html overlays (MA, MACD, RSI, S1/S2) + Bull/Base/Bear rail stub + STOCK_OVERLAYS.md.
Then stop and report. P1 = SEPA-TW (RS vs 0050) + drawings. P2 = local LLM evidence + frozen hit-rate.
Do not copy their Electron/core into this repo. Do not touch FundFlo slim. Box crons stay paused.
Optional: they may install Kansoku.app themselves for US/HK/A.
```
