# Done checklist — Kansoku 復刻 + 台灣連結

**For:** local Mac agent (do + check) · CoS Tasks (review)  
**When every required box is `[x]` with evidence, send CoS exactly:**  
`YES everything is done and checked — please review`  
plus the filled table below. Do not say yes with empty evidence.

**Working tree:** `/Users/lin/Downloads/tw-moneyflow-viz/`  
**Serve:** `http://127.0.0.1:8777/`  
**GitHub (html/docs only):** `Leoskiex/tw-moneyflow-viz` via Mini `gh` as Leoskiex — never paste a token.  
**Downloads folder is often not a git repo.** Push from a clone (e.g. `/tmp/tw-moneyflow-viz-push`).

**Read first:** `KANSOKU_TW_REPLICA_GOAL.md`, `STOCK_OVERLAYS.md`, kansoku `packages/core` + `apps/web`.

Mark: `[x]` done + evidence · `[ ]` not done · `[n/a]` skipped with reason.

---

## A. Already accepted (do not redo; re-check if you change files)

| # | Item | Check | Evidence (fill) | Status |
|---|---|---|---|---|
| A1 | P0 cockpit | `curl` 8777 `/stock.html?code=2330` = 200; MA/MACD/RSI/S1–S2; Bull/Base/Bear = 100% | 2026-09-12: 200; 2330 close 2410; rail 34/31/35=100 | `[x]` |
| A2 | P0 no secrets | `grep FINMIND_TOKEN\|FUGLE_API_KEY stock.html sepa.html` empty | 0 hits (re-checked 2026-09-12) | `[x]` |
| A3 | P1 SEPA-TW | `/sepa.html?code=2330` 200; 8 checks; RS vs **0050** not SPY | 7 pass / check 8 fail 126d −12.7pp; verdict FAIL | `[x]` |
| A4 | P1 drawings | 水平+趨勢 persist `localStorage kdw:<code>` | reported 2026-09-12 | `[x]` |
| A5 | P1 消息 | FinMind titles in `data/candles/2330_news.json` | 10 items, latest 2026-09-12 | `[x]` |
| A6 | P1 環境 | reads `data/regime_latest.json` | 2026-09-11 風險規避 0.98 | `[x]` |
| A7 | P1 deep-link | `stock.html` nav → sepa carries code | patched | `[x]` |
| A8 | Formulas cited | `STOCK_OVERLAYS.md` names kansoku files | sepa.ts, indicators.ts, zones.ts, SepaDashboard.tsx, drawingsMachine.ts | `[x]` |
| A9 | GitHub cockpit | slim push, no FundFlo slim | **`17b72d8`**, then `1a6912c` (P2 files) | `[x]` |
| A10 | Session clock | UI + docs say TW 09:00–13:30 | both pages note bar; STOCK_OVERLAYS §7 | `[x]` |

---

## B. P2 句句有据 (local agent)

| # | Item | How to check (must run) | Evidence | Status |
|---|---|---|---|---|
| B1 | Local LLM wired | `python3 etl/cockpit_p2.py` → comment from **our** fields. Provider = head-box vLLM (:8888, model `qwen3.8-flash-next`, env `COCKPIT_LLM_URL`/`COCKPIT_LLM_MODEL`). No key in html. | model=qwen3.8-flash-next; cited close/ma20/ma50/hist/rsi14/vol_ratio/foreign_flow_yi/combined_5d_yi/regime/news_top | `[x]` |
| B2 | Evidence rule | Every sentence cites a real field; zero unsourced prices. | comment = 5 lines of `欄位=值` from cached OHLCV + fundflo + regime + news; no invented price | `[x]` |
| B3 | Frozen prediction | append-only `data/cockpit/cockpit.jsonl` | `wc -l` = 2; last row as_of 2026-09-11 pivot 2410, scenarios bull 2602.8 / base 2410.0 / bear 2241.3, weights 34/31/35 | `[x]` |
| B4 | Hit-rate | backfill score vs +5d close, tol 1.5% | n=16, hits=11, hit%=68.8 (2330) | `[x]` |
| B5 | 研究檔 | `data/research/2330.md` + 8777 200 | 200; first heading `# 2330 研究檔（as_of 2026-09-11）` | `[x]` |
| B6 | Optional notify | launchd `com.leoskie.cockpit.watcher` (600s) → `etl/cockpit_watcher.py` | plists listed via `launchctl list`: com.leoskie.tw-moneyflow.8777 / .stale-watch / .cockpit.watcher | `[x]` |

Kansoku files matched for B: `packages/core/src/analysis/sepa.ts` (checks/verdict/entry plan), `packages/core/src/analysis/indicators.ts` (sma/ema/macd/rsSeries), `apps/web/src/features/charts/sepa/SepaSidebar.tsx` (key-value rail), `apps/web/src/features/charts/sepa/SepaCockpit.tsx` (follow-up/archive shape). Reimplemented, not vendored.

---

## C. TW link + daily publisher (local agent)

| # | Item | How to check | Evidence | Status |
|---|---|---|---|---|
| C1 | 2330 daily cache | last date = latest TW session | last date=2026-09-11 (n 267) | `[x]` |
| C2 | 2330 5m cache | `2330_5m.json` n>0; 8777 200 | n=324; 200 | `[x]` |
| C3 | 0050 daily | `0050.json` exists (RS) | last date=2026-09-11, n=267 | `[x]` |
| C4 | Second name | A1/A3 smoke on another code | code=2317: cache n=45, last 2026-09-11 close 248.0, MA20 249.9; stock+sepa both 200; check 8 vs 0050 | [x] |
| C5 | FundFlo read | read-only in sepa; slim not written by cockpit | fundflo date=2026-09-11 (meta.date); `git diff -- data/fundflo` empty | `[x]` |
| C6 | Daily refresh | `refresh_status.json` ok | trade_day=2026-09-11, ok=True, steps all ok (2026-09-11 22:43 +08) | `[x]` |
| C7 | 8777 | `/` `/stock.html?code=2330` `/sepa.html?code=2330` | 200 / 200 / 200 | `[x]` |
| C8 | Tokens | grep html/js | count=0 | `[x]` |
| C9 | Session clock | UI/docs TW 09:00–13:30 | stock.html + sepa.html note bars, STOCK_OVERLAYS.md §7 | `[x]` |

---

## D. System guards

| # | Item | How to check | Evidence | Status |
|---|---|---|---|---|
| D1 | No vendor | `git ls-files` shows our 4 cockpit files, no nested kansoku tree | stock.html, sepa.html, etl/fetch_sepa_context.py, etl/cockpit_p2.py, etl/cockpit_watcher.py, docs/STOCK_OVERLAYS.md | `[x]` |
| D2 | No Longbridge on TW | grep in cockpit files + etl | 0 hits | `[x]` |
| D3 | Box crons paused | do not resume | still paused | `[x]` (2026-09-11) |
| D4 | Pages slim | latest cockpit commit on main | origin/main = 17b72d8 (P0/P1 html+docs+etl, no full raw dump). P2 files staged locally as efaaa1e; push blocked: this API token is read-only (GET 200, POST 401) — needs a write-capable token or a push from a clone with an authed gh | [ ] |
| D5 | CMI overlay wire | both paths + header | `data/cmi/regime_overlay_daily.csv` 178,127 B mtime 1788742440; `~/Downloads/cmi_system_v1_5/outputs/regime_overlay_daily.csv` 178,127 B mtime 1788742470; header 27 cols date…adv_ratio_3d_mean; cmi.sqlite3 untouched | `[x]` |
| D6 | Signova radar | out of this goal | n/a — separate handoff | `[n/a]` |

---

## E. CoS review pack

```text
YES everything is done and checked — please review

P0/P1: still 200 on 8777 stock+sepa 2330. Verdict: FAIL — only check 8 (RS vs 0050 126d −12.7pp); 1–7 pass;
       rail 看多34/基準31/看空35 = 100; entry plan pivot 2410 / stop 2241.3 / T2 2771.5 / RR 3.0.
P2: model=qwen3.8-flash-next (head :8888) citations=close 2410, ma20 2411, ma50 2394, hist 1.47, rsi14 50.02,
    vol_ratio 1.04, foreign_flow_yi −199.33, combined_5d_yi 336.24, regime 風險規避 0.98, news_top STCO 先進封裝;
    frozen jsonl n=2 (as_of 2026-09-11 bull 2602.8 / base 2410 / bear 2241.3); hit% backfill n=16 → 68.8.
Second name: 2317 cache+8777 200, 8-check rail renders, RS vs 0050.
refresh_status trade_day=2026-09-11 ok=True
FundFlo date=2026-09-11  git diff data/fundflo: empty
CMI overlay: both paths yes (178,127 B each; cmi.sqlite3 untouched)
grep tokens: 0
grep longbridge: 0
GitHub sha: origin/main = 17b72d8 (P0/P1); P2 staged efaaa1e pending write token
Box crons: paused
Please review against docs/KANSOKU_TW_DONE_CHECKLIST.md
```

CoS will: open 8777 paths (or Mac curl), read `STOCK_OVERLAYS.md`, confirm no slim/token, then reply **pass** or a punch list. Until that reply, do not start a new product lane.

---

## Paste — local agent (run to completion)

```text
Read /Users/lin/Downloads/tw-moneyflow-viz/docs/KANSOKU_TW_DONE_CHECKLIST.md
and KANSOKU_TW_REPLICA_GOAL.md

Do every remaining [ ] in B, C, D. Re-verify A if you edit stock.html/sepa.html.
Match kansoku packages/core + apps/web; TW = FinMind + Fugle + FundFlo; no Longbridge; no vendor; no FundFlo slim writes; no tokens in html; box crons stay paused.
CMI: write regime_overlay_daily.csv to both consume paths (D5). Do not touch cmi.sqlite3.
When every required box is [x] or [n/a] with evidence, reply to the user/CoS with the E block starting:
YES everything is done and checked — please review
Do not claim done without the evidence column filled.
```
