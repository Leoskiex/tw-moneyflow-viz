# TW Money-flow Viz（錢往哪流）

Taiwan stock **chip / money-flow** static dashboard + deterministic (non-LLM) daily digest.

- **Live:** GitHub Pages (see repo About → Homepage)
- **Local:** `python3 -m http.server 8777` → http://127.0.0.1:8777/

## Layout

| Path | Role |
|------|------|
| `index.html` / `app.js` | Dashboard |
| `digest.html` | Copyable non-LLM daily digest |
| `data/` | Prebuilt curated / screens / regime / digest |
| `etl/` | Python builders (run locally; needs TWSE/TPEx access) |
| `fund-flow.html` + `js/fundflo_model.js` | FundFlo 近5日資金四象限（共用公式） |
| `docs/FUNDFLO_CONTRACT.md` | 共用欄位／單位契約 |
| `data/fundflo/` | `latest.json` / `series_top.json` / `by_date/` |

### FundFlo ETL

```bash
python3 etl/test_fundflo_model.py
TWSE_RAW_DIR=/path/to/raw python3 etl/build_fundflo_features.py
# curated 無價且無 raw 時仍會寫 fixture；有 raw 則 foreign_flow_yi = foreign_net(千張)×price/100
```


## Not published

- `raw/` day dumps (regenerate yourself)
- Personal machine paths / secrets

Heuristic labels only — **not investment advice**.

## License

MIT
