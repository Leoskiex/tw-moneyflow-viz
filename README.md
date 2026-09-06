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

## Not published

- `raw/` day dumps (regenerate yourself)
- Personal machine paths / secrets

Heuristic labels only — **not investment advice**.

## License

MIT
