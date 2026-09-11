# Local-agent handover ownership (after box crons paused)

**As of:** 2026-09-11 ~21:55 Asia/Taipei · **all daily lanes landed**  
**Trigger:** User → AISTOCKMAP paused box money-flow routines; **local Mac agent owns daily updates**.  
**CoS:** chase every bot that writes raw / Pages / 8777 / ETL / FundFlo / candles / ETF / screens / digest.

AISTOCKMAP paused:

- `tw-money-flow-daily-etl` (18:30)
- `tw-money-flow-etl-retry-20-45`
- `tw-money-flow-regime-digest` (19:00)
- `tw-quarter-backfill` (Sun 11:00)

---

## Status board

| Lane | Owner bot | Manual for local agent | Status |
|---|---|---|---|
| Daily T86 / FundFlo slim / Pages / 8777 | AISTOCKMAP → **local** | `docs/LOCAL_AGENT_HANDOFF.md` §3 + `docs/FUNDFLO_FULL_HISTORY_HANDBOOK.md` | **Done 2026-09-11:** §3 PAUSED + Mac commands / secrets / Pages / 8777 / failure modes. |
| Research layer (regime digest, action-radar, 6-layer jobs) | AISTOCKMAP | same `LOCAL_AGENT_HANDOFF.md` §3.8 | **Done:** marked optional / out-of-daily slim; script table listed. |
| FinMind daily candles | AISTOCKMAP | `docs/FINMIND_CANDLES.md` + `FINMIND_INTEGRATION.md` | Docs present; **optional satellite**. Local must set `FINMIND_TOKEN` on Mac if used. |
| Fugle 5m/15m/60m | AISTOCKMAP | `docs/FUGLE_CANDLES.md` | Docs present; **optional**. Local must set `FUGLE_API_KEY` on Mac if used. |
| Active ETF adapters + fund-flow UI cadence | 反向破解 → **local** | [`ETF_UI_LOCAL_HANDOFF.md`](./ETF_UI_LOCAL_HANDOFF.md) (+ schema in `ACTIVE_ETF_HOLDINGS.md`) | **Landed** 2026-09-11: issuers, fetch cadence, day-lag, Pages/8777 paths, no secrets, failure modes. T86 SoT untouched. |
| CMI consume FundFlo T−1 | CMI SYSTEM | [`CMI_CONSUME_HANDOFF.md`](./CMI_CONSUME_HANDOFF.md) | **Done 2026-09-11:** overlay CSVs into viz `data/cmi/` + `cmi_system_v1_5/outputs/`; do not touch `cmi.sqlite3`; CMI does not publish Pages/8777/slim. |
| Signova-style signal radar + 目標價 | CoS Tasks (spec) / local implement | `docs/SIGNAL_RADAR_LOCAL_HANDOFF.md` + `/workspace/signova-re/` | Spec ready; **not** part of daily FundFlo slim. |

---

## Local agent daily (intended, after manuals land)

1. After TWSE T86 (~18:00 Taipei): `refresh_daily.py` on Mac (FundFlo slim + ETF batch).  
2. Optional 20:45: margin catch-up.  
3. Sync Mac 8777 + push Pages (`Leoskiex/tw-moneyflow-viz`).  
4. Optional: FinMind candles watchlist; Fugle TFs **not** required for FundFlo.  
5. **Do not** resume AISTOCKMAP box crons unless user says so.

