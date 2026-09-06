# Date switching (curated TWSE backfill)

## What changed
- Server-side ETL: `/workspace/twse-trading/build_curated.py` reads local TWSE raw + `TW_TOPIC_MEMBERS.json` and writes:
  - `data/curated/YYYY-MM-DD.json` (one per trade day)
  - `data/curated/index.json` (oldest → newest)
  - `data/history_kpi.json` (60d trend series)
- UI loads curated JSON via `fetch` (needs HTTP server). Header has `‹` / date select / `›`; default = latest date.
- Trend chart uses full `history_kpi.json` with a dashed marker on the selected day.
- Main view no longer depends on `data.js` / `MF_SAMPLE` (file kept as unused fallback only).

## Units
| Field | Unit | Source |
|-------|------|--------|
| market foreign/trust/dealer | 億元 | BFI82U 元 ÷ 1e8 |
| total_amount | 億元 | MI_INDEX / FMTQIK |
| margin_balance / margin_delta | 億元 | MI_MARGN 融資金額(仟元) ÷ 1e5 |
| short_balance (market) | 千張 | 融券交易單位 ÷ 1000 |
| daytrade_pct | % | TWTB4U 金額占市場比重 |
| stock foreign/trust/dealer/inst_net | **千張** | T86 股數 ÷ 1e6 |
| stock amount | 億元 | MI_INDEX 成交金額 ÷ 1e8 |
| stock margin_delta | 張 | MI_MARGN_ALL tables[1] |
| short_sell / sbl_sell | 張 | TWTASU 數量 |

## Rebuild
```bash
python3 /workspace/twse-trading/build_curated.py
# serve
cd /workspace/tw-moneyflow-viz && python3 -m http.server 8765 --bind 127.0.0.1
```

## Notes
- No live TWSE calls in the UI path.
- Primary topic: preferred ids (e.g. wafer-foundry for 2330/2303, ai-server-odm for ODM names) else first membership.
- Skipped days without T86/BFI82U (e.g. 2026-07-10 in this backfill).
