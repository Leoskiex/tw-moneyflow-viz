# Goal — Kansoku **product parity** on TW (P3)

**As of:** 2026-09-13 · CoS Tasks  
**Why:** P0–P2 CoS-pass was **our checklist**, not their desktop. SEPA **math** ≈ `sepa.ts`. The app is still a cousin.

**North star:** 8777 cockpit **behaves** like the three Kansoku shots (个股驾驶舱 / SEPA / 盘面) on **TW names**.  
Read their source and match. Do not vendor the repo / `Kansoku.app`.

```text
kansoku
  packages/core/src/analysis/sepa.ts
  packages/core/src/analysis/zones.ts
  packages/core/src/analysis/indicators.ts   # macd hist = 2*(DIF−DEA)
  apps/web  SepaDashboard / drawings / follow-up panel
TW feeds (unchanged)
  FinMind daily · Fugle 5m/15m/60m · FundFlo slim read-only
```

**Still skip:** Longbridge, Electron/⌘T/Sparkle, Pro `pro.enc`, SPY heatmap, US session clock.

**P0–P2 stay.** Do not rip `stock.html` / `sepa.html` for a rewrite. Patch toward parity.

When every required row in §3 is `[x]` with evidence, send CoS:  
`YES P3 parity is done and checked — please review`

---

## 1. Who

| Who | Does |
|---|---|
| **Local agent (Mini)** | All UI + JS + etl. Work in `/Users/lin/Downloads/tw-moneyflow-viz/` |
| **CoS** | This goal, review gate, slim push via Mini `gh` (Leoskiex) if their token 401s |
| **AISTOCKMAP** | Only if candle JSON **contract** breaks |
| **FundFlo / CMI** | Slim + overlay stay as they are; cockpit **reads** |

Hard no: keys in html, `data/fundflo/*` writes, box cron resume, `cmi.sqlite3`, Longbridge for 2330.

---

## 2. Build order (do in this order)

### P3a — chart truth (do first)

Match `sepa.ts` `detectMarkers` + `zones.ts` + `indicators.ts` `macd()`.

| # | Item | Check |
|---|---|---|
| A1 | MACD hist = `2*(DIF−DEA)` on `stock.html` (kansoku). Update `STOCK_OVERLAYS.md`. Re-quote 2330 last bar. | hist was +2.07 (1×); new value ≈ **+4.14** |
| A2 | Markers on **daily** sepa (and stock daily): climax top (down bar, vol ≥ 2.5×20MA, local high), 跌破 MA50, 跌破 MA200, 52w 高 square. 财报 `E` if we have a date list (FinMind/MOPS or `[n/a]` + empty array). | 2330 shows 52w 高 at least; paste marker list |
| A3 | `zones.ts`: volume profile (lookback 120, bins 30) + default 价值区 / 成交密集区 lines on sepa main pane | screenshot or price levels listed |
| A4 | Live Fugle poll **while chart open**: if `*_5m.json` (or 15m/60m) older than N min, `etl/fetch_fugle_candles.py` for **that code only**, then redraw. Token env-only. No poll when tab hidden. | DevTools: refetch after interval; token not in JS |
| A5 | Strong Buy rule from `autoVerdict`: 8 pass + price in pivot~pivot+5% + vol ≥ 1.5×20MA → label Strong Buy (still no VCP auto-detect) | document on a name or “2330 still FAIL so n/a” |

### P3b — 句句有据 UI (after A)

Match their follow-up panel, not another jsonl-only script.

| # | Item | Check |
|---|---|---|
| B1 | Floating 「凭什么」 panel on `stock.html` (drag / close). Reads last comment + citations. | 8777, 2330, panel opens |
| B2 | AI / rule levels drawn **purple dashed** on the chart; toolbar 「只清 AI 线」. Persist `source=ai` vs user drawings. | 2 line types in store |
| B3 | Archive UI: frozen rows from `cockpit.jsonl` listed; **cannot edit** text; new run **appends**. Hit-rate % visible (reuse 68.8% backfill or recompute). | try-edit fails; n shown |
| B4 | Empty panel suggests **3 questions** (from our fields, not fluff). | 3 strings cited to fields |
| B5 | 研究檔: `data/research/2330.md` linked from the panel; 2317 has a file after one run | 200 |

### P3c — 盘面 (TW, not US heatmap)

Do **not** clone SPY/QQQ/VIX tiles.

| # | Item | Check |
|---|---|---|
| C1 | From `index.html` / `fund-flow.html` name click → `stock.html?code=` and `sepa.html?code=` | 2 links work |
| C2 | SEPA 环境 tab already has regime + 外资; add **主動 ETF Δ** read from `data/etf/` latest if present | one ETF line or n/a |
| C3 | TW clock 09:00–13:30 still labeled | already A10; keep |

---

## 3. Done table (local agent fills)

Mark `[x]` + evidence. Required = all P3a + P3b + C1. C2 may be `[n/a]`.

| # | Status | Evidence |
|---|---|---|
| A1 MACD 2× | `[x]` | 2330 hist=+3.9625 (DIF 16.2914 / DEA 14.3102; 2× per indicators.ts macd()) |
| A2 markers | `[x]` | n=16; 2026-06-23 52w高 sq 2535; 08-24 / 09-02 跌破MA50; climax @2.5×vol20; E=[] no date list |
| A3 zones | `[x]` | MA50 2346.12–2441.88; 價值區 1972.42–2260.88; POC 2380.00–2405.83; 密集 2328.33–2431.67 (vp 120/30/60%) |
| A4 live 5m | `[x]` | setInterval 30s + `_=` bust + visibilitychange kick; hidden→skip; token grep 0 in 4 html |
| A5 Strong Buy | `[x]` | n/a on 2330: FAIL(check8 only), ext +0.67%, vol_ratio 1.0408 <1.5 → stays WATCH |
| B1 凭什么 | `[x]` | #panelBtn→#panel (2330, 8777, 200): frozen comment + 3 cited Qs + close |
| B2 purple AI | `[x]` | AI dashed #9c27b0 + user solid #f7c945; store kdw:2330 / kdw:2330:ai; 「只清 AI 線」 |
| B3 archive | `[x]` | jsonl n=5 (2317×1 + 2330×4, append-only); backfill n=16 hits=11 = 68.8%; md read-only |
| B4 3 questions | `[x]` | Q1 rsi14/hist/vol_ratio; Q2 foreign_flow_yi/combined_5d_yi; Q3 regime+conf vs 0050 |
| B5 research | `[x]` | data/research/2330.md + 2317.md (argv-capable cockpit_p2.py); both 200 on 8777 |
| C1 deep-links | `[x]` | index.html code→stock.html?code=, name→sepa.html?code=; fund-flow rank-item K線/SEPA |
| C2 ETF line | `[x]` | data/etf/00981a/holdings_latest.json 2026-09-11; 2330 weight 10.27% (00981A) |
| Guards | `[x]` | grep token 0 (4 pages), longbridge 0, `git diff -- data/fundflo` empty, box crons paused |

**E block when full:**

```text
YES P3 parity is done and checked — please review
A1 hist= …  A2 markers= …  A3 zones= …
A4 poll= …  A5 …
B1–B5 …
C1 … C2 …
grep tokens: 0  longbridge: 0  fundflo diff: empty
GitHub sha: …
Please review against docs/KANSOKU_TW_PARITY_GOAL.md (not only 8777 200).
```

CoS review **must** open kansoku `sepa.ts` / `zones.ts` next to the pages — not checklist-only.

---

## 4. Paste — local agent

```text
Read /Users/lin/Downloads/tw-moneyflow-viz/docs/KANSOKU_TW_PARITY_GOAL.md

P3: product parity with kansoku on TW. P0–P2 stay; patch them.
Order: P3a (MACD 2×, detectMarkers, zones.ts, live Fugle poll while open, Strong Buy rule) then P3b (凭什么 panel, purple AI lines, frozen archive UI, 3 questions) then C1 deep-links.
Read github.com/kansoku-trade/kansoku packages/core sepa.ts zones.ts indicators.ts and the web dashboard. Match behavior. RS vs 0050. No Longbridge. No vendor. No FundFlo slim writes. No tokens in html. Box crons paused.
Cite each kansoku file you matched in STOCK_OVERLAYS.md.
When the §3 table is full, reply:
YES P3 parity is done and checked — please review
```
