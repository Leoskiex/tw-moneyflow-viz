# FundFlo 共用資金流契約

本文件定義 `tw-moneyflow-viz` Feature Store／ETL 與瀏覽器共用層的欄位與公式。  
消費端（含 `aistockmap-clone`）應引用同一契約，勿各自重寫。

參考來源：FundFlo 試用站反向拆解（`model.mjs` / `app.js` / `turnover-data.js`）與 `FUNDFLO_SHARED_SPEC.md`。

## 視窗

`WINDOW = 5` 個交易日。對回放日 `frame`（0-based，可為浮點）：

```
end = frame + WINDOW
start = end - WINDOW + 1   # 閉區間 [start, end]，長度 5
```

每個畫面用「該日往前 5 個交易日」，全市場普通股重算後再取 Top N。

播放時 `frame` 為浮點：`floor(frame)` 與 `ceil(frame)` 兩幀的 `state()` 以 `ease(t)=t²(3-2t)` 插值（見 `interpolateState` / `interpolate_state`）。

## 模式

| mode | 說明 |
|------|------|
| `foreign` | 外資估算淨額 |
| `etf` | 主動式 ETF 持股增減估算（standalone） |
| `combined` | 外資 + 主動式 ETF |
| `turnover` | 成交熱度（普通股） |

## 單位（寫死）

| 欄位 | 單位 | 備註 |
|------|------|------|
| `shares` | 股 | 外資買賣超股數；顯示張＝÷1000 |
| `foreign_flow_yi` | 億元 | 見下方換算 |
| `etf_flow_yi` | 億元 | 主動式 ETF 持股增減估算；無資料則 0 |
| `combined_flow_yi` | 億元 | `foreign_flow_yi + etf_flow_yi` |
| `amount` | 億元 | 當日成交金額（curated 已是億） |
| `average5` | 億元 | 前 5 個交易日成交金額平均（不含當日） |
| `change_pct` / `turnover_change` | % | `(amount/average5 - 1)*100` |
| `market_share` | % | `amount / Σamount * 100`（當日普通股） |
| `daily_ret` / `return` | % | 當日漲跌幅（curated `change`） |
| `cumulative_return` / `rolling_ret_5d` | % | 近 5 日累計漲跌幅 |
| 既有 curated `foreign_net` | **千張** | Feature Store 舊欄；**勿與億元混用** |

### curated schema 實測（重要）

`data/curated/*.json` 的 `stocks[]` **沒有** `close`／均價欄位。  
`foreign_net` 由 ETL 以「股數 ÷ 1e6」寫入，meta 標 `unit_inst_stock: 千張`：

- **1 千張 = 1,000,000 股 = 1,000 張**
- `shares = foreign_net × 1e6`
- 優先：`foreign_flow_yi = shares × 個股均價（缺則收盤） / 1e8`
- 等價：`foreign_flow_yi = foreign_net × price / 100`

> ⚠ 若誤把「千張→股」當成 ×1000（把千張當成千股），會得到  
> `foreign_net × close / 1e5`，比真實值小 **1000 倍**。  
> 本契約採 **`/100`**（與 `build_curated.py` 的 `f/1e6` 一致）。

建檔時若 curated 無價：`etl/build_fundflo_features.py` 可選讀 TWSE `MI_INDEX` raw（`--raw-dir`／`TWSE_RAW_DIR`）取均價＝成交金額÷成交股數，缺則收盤。無價則該列 `foreign_flow_yi` 為 `null`（仍保留 `shares`）。

Curated 路徑：優先 repo `data/curated`；否則 `TW_VIZ_CURATED`／`/workspace/tw-moneyflow-viz/data/curated`。

## flowOf

```
flowOf(day, mode):
  etf       → day.etf_flow_yi
  combined  → day.foreign_flow_yi + day.etf_flow_yi
  turnover  → day.amount          # size / ranking default
  foreign   → day.foreign_flow_yi
```

## 核心指標（外資／ETF／綜合）

```
rolling_5d     = sum(flowOf(d) for d in days[start..end])
prior_rolling  = sum(flowOf(d) for d in days[start-1..end-1])  # 缺完整前窗則 = rolling
momentum_5d    = rolling_5d - prior_rolling
rolling_ret_5d = (close[end] / close[start-1] - 1) * 100   # 無收盤則串 daily change%
daily_flow     = flowOf(days[end])
```

輸出欄名：

- `rolling_foreign_5d_yi` / `momentum_foreign_5d_yi`
- `rolling_etf_5d_yi` / `momentum_etf_5d_yi`
- `rolling_combined_5d_yi` / `momentum_combined_5d_yi`
- `rolling_ret_5d`
- `foreign_flow_yi`, `etf_flow_yi`, `combined_flow_yi`, `shares`

## 成交熱度（turnover）— 對齊 FundFlo `model.mjs`

```
flow            = changePct          # 圖橫軸：成交增溫
momentum        = return / daily_ret # 圖縱軸：當日股價漲跌
rolling         = amount             # 泡泡大小／預設排行
rollingRet      = cumulativeReturn   # 近5日累計漲跌
average5        = 前5日平均成交金額
marketShare     = 全市場普通股成交占比
turnoverChange  = changePct
```

排行方向：`turnover`＝成交金額、`surge`＝增溫、`share`＝占比。

排除：ETF／ETN／權證／特別股／存託憑證（與 `is_common` 過濾）。

## 主動式 ETF

`etl/build_fundflo_features.py` 掃描 `data/etf/*/`（holdings、holdings_latest、per-date JSON、latest.json）：

- 對每一檔主動式 ETF，取 `share_delta`；若無則用連續兩日 `share` 差
- `etf_flow_yi = Σ (share_delta × price / 1e8)` 跨所有可用 ETF
- meta：`active_etfs_used`、`etf_flow_nonzero_stock_days`
- 磁碟上只有 00981A 時仍輸出完整 etf 模式欄位，不伪造其他 ETF

## 正規化（四象限圖）

```
normalize(v, s) = clamp( asinh(v/s) / asinh(3), -1, 1 )
```

`s_x`／`s_y` 取 |flow|／|momentum| 約 85 百分位（turnover 的 flow＝changePct）。  
泡泡色依 `rolling_ret`（**紅漲綠跌**）。

## 插值（UI）

```
interpolateState(a, b, t):
  tt = ease(t)   # t²(3-2t)
  blend numeric keys: flow, momentum, rolling, rollingRet,
                      average5, marketShare, turnoverChange, …
```

Python：`interpolate_state`；JS：`FundFloModel.interpolateState`。

## 實作位置

| 層 | 路徑 |
|----|------|
| Python 純函式 | `etl/fundflo_model.py` |
| 測試 | `etl/test_fundflo_model.py` |
| 瀏覽器純函式 | `js/fundflo_model.js` |
| ETL 輸出 | `etl/build_fundflo_features.py` → `data/fundflo/` |
| UI | `fund-flow.html`（消費 JSON + 共用 JS；rAF 分數 frame） |

## JSON 輸出

`latest.json`（無完整 series）與 `series_top.json`（多日回放）的股票列可含：

```json
{
  "code": "2330",
  "name": "台積電",
  "foreign_flow_yi": 12.3,
  "etf_flow_yi": 0.4,
  "combined_flow_yi": 12.7,
  "rolling_foreign_5d_yi": 40.1,
  "momentum_foreign_5d_yi": 5.2,
  "rolling_etf_5d_yi": 1.2,
  "momentum_etf_5d_yi": 0.3,
  "rolling_combined_5d_yi": 41.0,
  "momentum_combined_5d_yi": 5.5,
  "rolling_ret_5d": 2.15,
  "shares": 1230000,
  "amount": 711.5,
  "average5": 650.2,
  "change_pct": 9.43,
  "turnover_change": 9.43,
  "market_share": 3.21,
  "daily_ret": -0.62,
  "cumulative_return": 2.15
}
```

`series_top.json` 的 `days[]` 必須含多日序列（foreign／etf／combined／turnover 皆可回放）。日更預設 `write_by_date=False`（slim）。
