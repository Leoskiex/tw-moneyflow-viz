# Topic taxonomy — single source of truth

**Policy (2026-09-16):** 群組／題材分類 **全站同一本**。AISTOCKMAP 地圖、FundFlo／泡泡／今日 curated、日後 SPA 盤面，**不得**各養一份 topic 表。

## SoT file
`tw-moneyflow-viz/data/TW_TOPIC_MEMBERS.json`

Also reachable as:
`aistockmap/topics/TW_TOPIC_MEMBERS.json` → symlink to the SoT (Mac).

Env override: `TW_TOPIC_MEMBERS=/absolute/path.json`

## Who must use it
| Consumer | How |
|---|---|
| `build_curated.py` | `TOPIC_PATH` resolves to SoT (env → viz data → aistockmap/topics) |
| FundFlo / bubble / 今日 | Read `topic` / `group` already stamped on curated → fundflo rows |
| AISTOCKMAP `:8765` 產業地圖 | Edit/display this same JSON — do not fork |
| SPA | Display/filter by same fields; never invent a parallel map |

## CMI
CMI sqlite `themes` is **legacy parallel**. Target: map or replace so day-op / research labels can join on **topic id** from SoT. Until that lands, **do not** present CMI themes as a second industry book in the SPA. Prefer showing FundFlo/`TW_TOPIC_MEMBERS` names when a code has both.

## Not the same (keep separate)
- TWSE official `sectors[]` (水泥、鋼鐵…) = exchange sector codes for breadth tables — **label as 證交所產業**, not 題材群組.
- `etl/tw_industry_map.json` = thin code→string helper — **deprecate toward SoT** when touched; do not grow it.

## Edit rule
One editor path: change SoT → rebuild curated/FundFlo (refresh_daily) → UI updates. No silent topic lists inside HTML/SPA.
