# FundFlo／台股資金流 — 全歷史整理手冊（給本地 agent）

> 寫給要在 **Mac／本地** 把「已下載的 raw」整理成可回放、可研究的 FundFlo 資料的 agent。  
> 日期基準：2026-09-11（Asia/Taipei）。  
> 相關契約：`docs/FUNDFLO_CONTRACT.md`、總交接：`docs/LOCAL_AGENT_HANDOFF.md`。

---

## 0. 先回答：「為什麼只有 40／60 天？」

**不是沒整理。** 三層資料狀態不同：

| 層 | 現況（box 實測 2026-09-11） | 說明 |
|----|------------------------------|------|
| **raw**（原始下載） | **~951 個交易日** `2023-01-02` → `2026-09-10` | TWSE／TPEx 日目錄已在 |
| **curated**（日快照整理） | **~651 天** `2024-01-02` → `2026-09-09` | 2024 起已整批 curate；**尚未含 2023** |
| **FundFlo `series_top.json`**（水流頁回放） | **刻意壓成 `keep_dates=40`**（曾用 `--max-dates 60` 重算） | **不是缺資料**，是 Pages／瀏覽器體積壓縮 |
| **FundFlo `by_date/`** | 日更常 **skip**（slim） | 完整逐日檔可選重建，體積大 |

所以：

1. **故事／研究用的 curated** ≈ 2024 至今，已有。  
2. **「錢怎麼流」頁只播最近 40 天**，因為 `etl/build_fundflo_features.py` 的 `_compact_series(..., keep_dates=40)`。  
3. **2023 raw 已下，但 curated／FundFlo 還沒吃 2023**（`curate_range.py` 預設 `START=2024-01-01`）。

本地 agent 的任務＝依下方步驟決定要「拉長回放窗」還是「補 2023 curated」還是「產出研究用全曆史 FundFlo」。

---

## 1. 目錄地圖（勿搞混）

假設本地與 box 對齊的兩棵樹：

```
twse-trading/                 # ETL／raw／腳本
  raw/YYYY-MM-DD/             # 原始日資料（勿 Path.iterdir 掃整棵）
  raw/manifest.json
  build_curated.py
  curate_range.py
  refresh_daily.py
  build_regimes.py
  …

tw-moneyflow-viz/             # 視覺／Pages 產物
  data/curated/YYYY-MM-DD.json
  data/curated/index.json     # ⚠ 可能過期，見 §5
  data/fundflo/latest.json
  data/fundflo/series_top.json
  data/fundflo/by_date/        # 可選
  etl/build_fundflo_features.py
  etl/fundflo_model.py
  fund-flow.html
  docs/FUNDFLO_CONTRACT.md
```

`refresh_daily.py` 會把 `tw-moneyflow-viz/etl` 加進 `sys.path` 後呼叫 `build_fundflo_features`。

---

## 2. 硬規則（本地必遵守）

1. **禁止**對巨大 `raw/` 用 `Path.iterdir()`／無界 `glob`（box 會掛；本地也可能極慢）。用 `ls`／明確日期迴圈。  
2. **單位**：curated `foreign_net`＝**千張**（1 千張＝1e6 股）；FundFlo `*_yi`＝**億元**；換算 `foreign_flow_yi = foreign_net * price / 100`（見契約）。  
3. **GitHub**：用已登入的 `gh`／`git push`，**禁止**在對話貼 `ghp_` token。  
4. **Pages 推送**：選擇性 sync（不要一次推全量 curated／features）。日更 slim：`latest.json` + `series_top.json`；全量 `by_date/` 通常**不要**上 Pages。  
5. UI 文案：繁中白話；故事頁禁中英混雜術語。

---

## 3. 你要達成的三種目標（選一種或依序做）

### 目標 A — 只把「水流回放」拉長（最常見）

**前提**：curated 2024→今已齊。  
**做**：重跑 FundFlo，**不要** `--max-dates`，並把 `keep_dates` 調大（例如 120／250），或另存研究檔。

### 目標 B — 補 2023 curated（raw 已有、整理層缺）

**前提**：`raw/2023-*` 存在。  
**做**：把 `curate_range.py` 的起始日改成 `2023-01-01`（或加 `--start`），跑完再跑 FundFlo。

### 目標 C — 研究用「全曆史 FundFlo」（本機磁碟）

**做**：全量 `build_fundflo_features.py`（無 `--max-dates`），**寫 `by_date/`**（不要 `--skip-by-date`），`series_top` 可另存 `series_research.json`（keep 全部或 250+）。  
**不要**把完整 `by_date/` 推進 GitHub Pages。

---

## 4. 步驟詳解

### 4.1 盤點現況（先做這個，寫進回報）

在 `tw-moneyflow-viz`／`twse-trading` 根目錄執行（用 shell `ls`，不要 Python `iterdir`）：

```bash
# raw 天數與起迄
ls twse-trading/raw | rg '^[0-9]{4}-' | sort | head -2
ls twse-trading/raw | rg '^[0-9]{4}-' | sort | tail -2
ls twse-trading/raw | rg -c '^[0-9]{4}-'

# curated 天數與起迄
ls tw-moneyflow-viz/data/curated | rg '^[0-9]{4}-.*\.json$' | sort | head -2
ls tw-moneyflow-viz/data/curated | rg '^[0-9]{4}-.*\.json$' | sort | tail -2
ls tw-moneyflow-viz/data/curated | rg -c '^[0-9]{4}-.*\.json$'

# FundFlo meta
python3 - <<'PY'
import json
from pathlib import Path
p=Path('tw-moneyflow-viz/data/fundflo/series_top.json')
d=json.loads(p.read_text())
m=d['meta']; s=d['series'][0]
print('keep_dates', m.get('keep_dates'), 'date', m.get('date'),
      'n_series', len(d['series']),
      'sample_days', len(s['days']), s['days'][0]['date'], '->', s['days'][-1]['date'])
PY
```

**期望**：raw 含 2023；curated 從 2024-01-02；series_top `keep_dates` 預設 40。

### 4.2（可選）補 curated — 含 2023 或補洞

腳本：`twse-trading/curate_range.py`  
預設 `START = "2024-01-01"`。

**補 2023：**

1. 改 `START = "2023-01-01"`，或加 CLI（若本地已 fork 出 `--start`）：  
   `python3 curate_range.py --start 2023-01-01`  
2. 確認 `build_curated.RAW_DIR`／`OUT_DIR` 指到你的本地路徑。  
3. 執行（可先 dry 看 log）：

```bash
cd twse-trading
python3 curate_range.py          # 預設只補缺／太小的檔
# 若要重算某段：python3 curate_range.py --force   # 很慢，慎用
```

4. 成功標準：  
   `data/curated/2023-01-*.json` 出現且單檔 ≳ 10KB；  
   curated 日期連續性可用「raw∩交易日 − curated」列 gap。

5. **重建 `data/curated/index.json`**（目前常過期，只剩近幾個月）：

```bash
# 用 ls 列出全部日期寫回 index（範例）
python3 - <<'PY'
import json, subprocess, re
from pathlib import Path
cur = Path('tw-moneyflow-viz/data/curated')  # 依本地實際路徑
out = subprocess.check_output(['ls', str(cur)], text=True)
dates = sorted(n[:-5] for n in out.split() if re.match(r'\d{4}-\d{2}-\d{2}\.json$', n))
(cur/'index.json').write_text(json.dumps(dates, ensure_ascii=False, indent=2), encoding='utf-8')
print(len(dates), dates[0], '->', dates[-1])
PY
```

### 4.3 重建 FundFlo（核心）

```bash
cd tw-moneyflow-viz

# A) 給 Pages／水流頁：長窗 series_top，不寫 by_date
#    先把 etl/build_fundflo_features.py 內 keep_dates/top_n 調到目標
#    建議 Pages：keep_dates=120, top_n=50（約數十 MB 內）
#    建議本機研究回放：keep_dates=250 或 =全部 curated 天數
python3 etl/build_fundflo_features.py \
  --skip-by-date \
  --raw-dir /絕對路徑/twse-trading/raw

# B) 本機研究全量（慢、佔磁碟）
python3 etl/build_fundflo_features.py \
  --raw-dir /絕對路徑/twse-trading/raw
  # 不要加 --skip-by-date、不要加 --max-dates
```

**改 keep_dates 的位置**（兩處常數要一致）：

- `_compact_series(..., keep_dates=40, top_n=50)` 預設參數  
- `write_outputs` 裡呼叫與 meta 寫入的 `keep_dates`／`top_n`

**禁止**為了「快」長期用 `--max-dates 60` 當正式產物（那只會讓回放又變短）。`--max-dates` 僅供除錯。

**成功標準：**

```text
series_top.meta.keep_dates == 你設的值
sample stock days 長度 ≈ keep_dates
meta.date == 最新 curated 日
price_hits >> price_miss（有接 MI_INDEX raw 均價／收盤）
fund-flow.html 載入後可「讓水流動」且泡泡明顯搬家
```

### 4.4（建議）同步 regimes／日更狀態

若補了 2023 或大段 curated：

```bash
cd twse-trading
python3 build_regimes.py    # 需涵蓋全部 curated 日（曾有只從 2026-03 標的問題）
# 然後視需要 screens / digest；日更可用 refresh_daily.py
```

### 4.5 推 GitHub Pages（選擇性）

只推：

- `fund-flow.html`、`js/fundflo_model.js`
- `data/fundflo/latest.json`、`data/fundflo/series_top.json`
- 必要時 `etl/build_fundflo_features.py`、`docs/*`

**不要推**：完整 `data/curated/*`、完整 `data/fundflo/by_date/*`、features／outcomes  bulk。

```bash
# 在已認證的 gh-pages 工作複本
git add … && git commit -m "…" && git push origin main
# 用 git／gh，禁止對話要 token
```

---

## 5. 已知坑

| 坑 | 症狀 | 處理 |
|----|------|------|
| `keep_dates=40` | 水流頁只有 ~1–2 個月 | 調大 keep_dates 後**全量**重跑（無 max-dates） |
| `--max-dates 60` | 以為「只有 60 天資料」 | 那是除錯參數；正式跑拿掉 |
| `curated/index.json` 過期 | index 只有 ~122 天 | §4.2 用 ls 重寫 |
| 日更 `write_by_date=False` | `by_date/` 很少 | 正常；研究時本機全量寫 |
| `etf_flow_yi`≈0 | 幾乎只有 00981A | 另案：多檔主動 ETF（反向破解進行中） |
| manifest 未前進 | curated 停在舊日 | 修 `raw/manifest.json` `latest_trade_day` 再 curate |
| Path.iterdir on raw | agent 卡住 | 改 ls／日期列表 |

---

## 6. 建議預設（給本地 agent 的「直接做」清單）

若用戶說「把歷史整理出來給水流用」且磁碟充足：

1. 盤點 §4.1，回報 raw／curated／series_top 起迄。  
2. **若只要長回放**：把 `keep_dates` → **120**（Pages）或 **250**（本機），跑  
   `python3 etl/build_fundflo_features.py --skip-by-date --raw-dir …`（**無** max-dates）。  
3. **若要 2023**：`curate_range` 起始改 2023-01-01 → 跑完 → 重寫 index → 再跑 FundFlo。  
4. 煙測 `fund-flow.html` 播放。  
5. 選擇性 push Pages（latest + series_top + html）。  
6. 回報：新 `keep_dates`、series 天數、檔案 MB、是否含 2023。

---

## 7. 與「反向破解」的分工

- **反向破解**：多檔主動 ETF 頁籤、rAF 分數 frame、turnover 模式（在 `main` 上接）。  
- **本地／本手冊**：歷史 curated／FundFlo 天數與 `series_top` 長度、2023 補齊、本機 `by_date`。  
- 兩邊都維持：slim 日更＝`latest` + `series_top`；契約欄位不變。

---

## 8. 一頁口語對用戶

> 2023～現在的原始檔早就下載了；2024 到現在也整理成每日快照了。  
> 網站上的「水流」只播最近四十天，是故意壓小檔案，不是沒整理。  
> 若要看更長的水流或把 2023 也整理進去，照本手冊在本地跑即可。

