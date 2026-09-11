# FundFlo／台股資金流 — 全歷史整理手冊（給本地 agent）

> 寫給要在 **Mac／本地／有 raw 的環境** 把「已下載的 raw」整理成可回放、可研究的 FundFlo 資料的 agent。  
> 日期基準：2026-09-11（Asia/Taipei）· **rev2**（主動 ETF／UI 補齊後更新）。  
> 相關：`docs/FUNDFLO_CONTRACT.md`、`docs/ACTIVE_ETF_HOLDINGS.md`、`docs/LOCAL_AGENT_HANDOFF.md`。

---

## 0. 先回答：「為什麼只有 30／40／60 天？」

**不是沒整理。** 三層資料狀態不同：

| 層 | 現況（2026-09-11 rev2） | 說明 |
|----|-------------------------|------|
| **raw**（原始下載） | **~951 個交易日** `2023-01-02` → `2026-09-10` | TWSE／TPEx 日目錄已在（有 raw 的機器） |
| **curated**（日快照整理） | **~651 天** `2024-01-02` → `2026-09-09` | 2024 起已整批 curate；**尚未含 2023** |
| **FundFlo `series_top.json`** | ETL 預設 **`keep_dates` 約 36–40**；頁面開檔只播 **`PLAYBACK_DAYS=30`** | **不是缺資料**，是壓縮＋UI 窗 |
| **FundFlo `by_date/`** | 日更常 **skip**（slim） | 完整逐日檔可選重建，體積大 |

所以：

1. **故事／研究用的 curated** ≈ 2024 至今，已有。  
2. **「錢怎麼流」頁開檔播最近 30 日**（`fund-flow.html` 的 `PLAYBACK_DAYS`）；底層 series 需 ≥ 約 36 日（WINDOW=5）。  
3. **2023 raw 已下，但 curated／FundFlo 還沒吃 2023**（`curate_range.py` 預設 `START=2024-01-01`）。  
4. **Mac 上的 8777 複本常缺 `etl/`＋`raw/`** → 拉長 `keep_dates` 的重跑要在 **有 curated＋raw 的環境**（box／本地完整樹）做，再 slim sync 回 Mac／Pages。

---

## 1. 目錄地圖（勿搞混）

```
twse-trading/                 # ETL／raw／腳本
  raw/YYYY-MM-DD/
  raw/manifest.json
  build_curated.py
  curate_range.py
  refresh_daily.py            # 含非阻擋 active ETF batch → build_fundflo
  fetch_00981a.py
  active_etf/                 # registry＋adapters（若在 trading 樹）
  fetch_active_etf_holdings.py
  …

tw-moneyflow-viz/             # 視覺／Pages 產物
  data/curated/YYYY-MM-DD.json
  data/curated/index.json     # 可能過期，見 §5
  data/fundflo/latest.json
  data/fundflo/series_top.json
  data/fundflo/by_date/        # 可選
  data/etf/<code>/holdings/YYYY-MM-DD.json
  data/etf/<code>/holdings_latest.json
  etl/build_fundflo_features.py
  etl/fundflo_model.py
  etl/active_etf/*            # 若合在 viz 樹
  fund-flow.html              # 外資｜主動式ETF｜綜合｜成交熱度；rAF 插值
  docs/FUNDFLO_CONTRACT.md
  docs/ACTIVE_ETF_HOLDINGS.md
  docs/FUNDFLO_FULL_HISTORY_HANDBOOK.md  # 本檔
```

`refresh_daily.py` 把 `tw-moneyflow-viz/etl` 加進 `sys.path` 後呼叫 `build_fundflo_features`；主動 ETF batch 為非阻擋。

---

## 2. 硬規則（本地必遵守）

1. **禁止**對巨大 `raw/` 用 `Path.iterdir()`／無界 `glob`。用 `ls`／明確日期迴圈。  
2. **單位**：curated `foreign_net`＝**千張**；FundFlo `*_yi`＝**億元**；`foreign_flow_yi = foreign_net * price / 100`。  
3. **GitHub**：已登入 `gh`／`git push`；**禁止**對話貼 `ghp_`。  
4. **Pages slim**：`fund-flow.html`、`js/fundflo_model.js`、`data/fundflo/latest.json`＋`series_top.json`、`data/etf/**/holdings_latest.json`（至少統一四檔）。**不要**推全量 curated／features／`by_date/`。  
5. UI：繁中白話；故事頁禁中英混雜術語。  
6. **00981A 主線故事權重不改**；其它主動 ETF 只補強 `etf_flow_yi`。

---

## 3. 三種目標

### 目標 A — 拉長「水流」回放（§6 預設）

把 ETL `keep_dates` → **120**（Pages）或 **250**（本機研究），**無** `--max-dates`，`--skip-by-date` 可保留。  
成功：`series_top.meta.keep_dates` 與 sample `days` 長度一致；檔案 MB 可接受再 push。

### 目標 B — 補 2023 curated

`curate_range` 起始 `2023-01-01` → 重寫 index → 級聯 regimes／features／FundFlo／screens。

### 目標 C — 本機全曆史 FundFlo

全量跑、寫 `by_date/`；**勿**把完整 `by_date/` 推 Pages。

---

## 4. 步驟詳解

### 4.1 盤點

```bash
ls twse-trading/raw | rg '^[0-9]{4}-' | sort | head -2
ls twse-trading/raw | rg '^[0-9]{4}-' | sort | tail -2
ls tw-moneyflow-viz/data/curated | rg -c '^[0-9]{4}-.*\.json$'
python3 - <<'PY'
import json
from pathlib import Path
p=Path('tw-moneyflow-viz/data/fundflo/series_top.json')
d=json.loads(p.read_text()); m=d['meta']; s=d['series'][0]
print('keep_dates', m.get('keep_dates'), 'date', m.get('date'),
      'n_series', len(d['series']),
      'sample_days', len(s['days']), s['days'][0]['date'], '->', s['days'][-1]['date'])
PY
ls tw-moneyflow-viz/data/etf/*/holdings_latest.json
```

### 4.2 重寫 curated index（消「只有三月」）

用 `ls` 列出全部 `YYYY-MM-DD.json`，排序後寫回 `data/curated/index.json`（勿信過期 index）。

### 4.3 重建 FundFlo（拉長 keep_dates）

1. 改 `etl/build_fundflo_features.py`：`_compact_series` 預設與 `write_outputs` 呼叫／meta 的 `keep_dates`／`top_n` **兩處一致**。  
2. 建議 Pages：`keep_dates=120`, `top_n=50`。  
3. 執行（路徑依機器）：

```bash
cd tw-moneyflow-viz
python3 etl/build_fundflo_features.py \
  --skip-by-date \
  --raw-dir /絕對路徑/twse-trading/raw
# 不要加 --max-dates
```

4. 煙測 `fund-flow.html`（開檔約 30 日回放；拖軸可看 series 全長）。  
5. Slim sync Pages＋8777。

### 4.4 主動 ETF（已落地，細節見 ACTIVE_ETF_HOLDINGS.md）

- 路徑：`data/etf/<lowercase_code>/holdings/`  
- 統一啟用：`00981A`（priority 1）＋`00403A`／`00411A`／`00988A`（priority 2）  
- Registry 另有 00980A／00982A／… 登錄；來源優先投信官網／PCF／ezMoney  
- **新檔若只有 1 個持股日 → 隔日再抓才有 share 差分 → `etf_flow_yi` 才非零**；00981A 歷史差分仍可用  
- `build_fundflo` 聚合：各檔 consecutive share 差分 × price / 1e8 加總為 `etf_flow_yi`

### 4.5 screens／過期 caveat（仍欠）

- `data/screens/` 仍約自 2026-01 起 → 應對齊 curated 全曆重跑  
- lifecycle／tournament 文案若仍寫「約 60d／119 regimes」→ 清掉或重跑

---

## 5. 已知坑

| 坑 | 症狀 | 處理 |
|----|------|------|
| `keep_dates` 仍 36–40 | 底層回放短 | §4.3 → 120 |
| `PLAYBACK_DAYS=30` | 開檔只動 30 日 | 正常；改常數或拖軸看更長 series |
| `--max-dates 60` | 誤以為只有 60 天 | 正式跑拿掉 |
| `curated/index.json` 過期 | 顯示只有三月起 | §4.2 |
| Mac 缺 etl／raw | 無法在 8777 目錄重跑 | 在完整樹上跑完再 slim 拷回 |
| 新 ETF 單日持股 | `etf_flow` 仍稀 | 隔日再 fetch |
| 日更 skip by_date | by_date 很少 | 正常 |
| Path.iterdir on raw | agent 卡住 | 改 ls |

---

## 6. 建議預設（「直接做」清單）— §6 給有 raw 的 agent

反向破解／本地若已對過本節：

1. 盤點 §4.1。  
2. **`keep_dates` → 120**，跑 `build_fundflo_features.py --skip-by-date --raw-dir …`（**無** max-dates）。  
3. 確認 `series_top` meta＋sample days＝120；`etf_flow`／`active_etfs_used` meta 合理。  
4. Slim push／sync：fundflo 兩檔＋`holdings_latest`＋html／js。  
5. （可選）重寫 curated index；screens 回填；2023 curate。  
6. 回報：keep_dates、MB、etf_flow 非零檔數、是否含 2023。

> Mac-only 8777 樹：**不要**在缺 raw 時硬跑；改在 box／完整本地樹跑完再拷。

---

## 7. 與「反向破解」／AISTOCKMAP 的分工（rev2）

| 誰 | 負責 |
|----|------|
| **反向破解** | 主動 ETF registry／fetch、fund-flow 四頁籤、rAF 插值、turnover、**有 raw 時把 keep_dates→120** |
| **AISTOCKMAP（本 agent）** | Pages／8777 slim sync、regime／故事層、交接文件、與 CMI 協作 |
| **用戶本地 agent** | 可選：2023 curate、screens 全曆、tournament 重跑、本機 by_date |

兩邊都維持：slim 日更＝`latest`＋`series_top`（＋ holdings_latest）；契約 WINDOW=5。

---

## 8. 一頁口語對用戶

> 2023～現在的原始檔早就下載了；2024 到現在也整理成每日快照了。  
> 網站開檔只自動播最近約三十天，底層系列大概四十天，是故意壓小，不是沒整理。  
> 主動 ETF 已能抓多檔（統一姊妹檔已開）；新檔要兩天持股才算得出流進流出。  
> 若要把回放拉到約一百二十天，在有 raw 的機器照 §6 跑即可。

---

## 9. moneyflow「計算層」完成度（2026-09-11 rev2）

### 已拉長到 2024→今（~651 交易日）

| 層 | 狀態 |
|----|------|
| curated 日 JSON | 已完成 2024-01-02 → 2026-09-09 |
| regimes.json | 已完成 ~651 |
| features／outcomes／signals／lifecycle by_date | 已完成 ~651 |

### UI／主動 ETF（本日已合 main）

| 項 | 狀態 |
|----|------|
| fund-flow 外資／主動式ETF／綜合／成交熱度 | 已完成 |
| rAF＋分數 frame 插值 | 已完成 |
| `PLAYBACK_DAYS=30` | 已完成 |
| `data/etf/*/holdings` 多檔＋統一 00981A／00403A／00411A／00988A | 抓取已落地 |
| `etf_flow_yi` 聚合進 fundflo | 已接上；新檔差分仍稀疏（需隔日） |

### 仍然偏短／未做完

| 層 | 現況 | 下一步 |
|----|------|--------|
| curated **index.json** | ~122 天（2026-03 起） | §4.2 重寫 |
| **screens/** | ~166 天（2026-01 起） | 對齊 curated 重跑 |
| FundFlo **series_top keep_dates** | 仍 ~36–40 | **§6 → 120**（有 raw 的環境） |
| FundFlo **by_date** | 日更 slim | 本機研究再全寫 |
| lifecycle／tournament 舊 caveat | ~60d／119 | 清理或重跑 |
| **2023** curated 級聯 | 未做 | 目標 B |
| 新 ETF 多日差分 | 多半 1 日快照 | 日更持續 fetch |

### 「六十天／三月」從哪來？

早期短樣本 validation；後來主層扩到 ~651，但 **index／screens／series_top／部分報告沒全部跟着重跑**，說法會並存。以本表「仍然偏短」為準。

### 優先序（rev2）

1. **§6 `keep_dates→120`**（有 raw；反向破解已接）→ slim sync  
2. 重寫 curated index  
3. screens 全曆  
4. 持續主動 ETF 日揭（讓姊妹檔出現差分）  
5. （可選）2023＋tournament 重跑  
