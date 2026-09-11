# FundFlo 共用資金流契約

本文件定義 `tw-moneyflow-viz` Feature Store／ETL 與瀏覽器共用層的欄位與公式。  
消費端（含 `aistockmap-clone`）應引用同一契約，勿各自重寫。

參考來源：FundFlo 試用站反向拆解（`model.mjs`）與 `FUNDFLO_SHARED_SPEC.md`。

## 視窗

`WINDOW = 5` 個交易日。對回放日 `frame`（0-based）：

```
end = frame + WINDOW
start = end - WINDOW + 1   # 閉區間 [start, end]，長度 5
```

每個畫面用「該日往前 5 個交易日」，全市場普通股重算後再取 Top N。

## 單位（寫死）

| 欄位 | 單位 | 備註 |
|------|------|------|
| `shares` | 股 | 外資買賣超股數；顯示張＝÷1000 |
| `foreign_flow_yi` | 億元 | 見下方換算 |
| `etf_flow_yi` | 億元 | 主動式 ETF 持股增減估算；無資料則 0 |
| `combined_flow_yi` | 億元 | `foreign_flow_yi + etf_flow_yi` |
| 既有 curated `foreign_net` | **千張** | Feature Store 舊欄；**勿與億元混用** |
| curated `amount` | 億元 | 成交金額 |
| curated `unit_share` meta | 張 | 融資等餘額用語，與 `foreign_net` 不同 |

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

## flowOf

```
flowOf(day, mode):
  etf       → day.etf_flow_yi
  combined  → day.foreign_flow_yi + day.etf_flow_yi
  foreign   → day.foreign_flow_yi
```

## 核心指標

```
rolling_5d     = sum(flowOf(d) for d in days[start..end])
prior_rolling  = sum(flowOf(d) for d in days[start-1..end-1])  # 缺完整前窗則 = rolling
momentum_5d    = rolling_5d - prior_rolling
rolling_ret_5d = (close[end] / close[start-1] - 1) * 100
daily_flow     = flowOf(days[end])
```

輸出欄名：

- `rolling_foreign_5d_yi` / `momentum_foreign_5d_yi`
- `rolling_combined_5d_yi` / `momentum_combined_5d_yi`
- `rolling_ret_5d`
- `foreign_flow_yi`, `etf_flow_yi`, `combined_flow_yi`, `shares`

## 正規化（四象限圖）

```
normalize(v, s) = clamp( asinh(v/s) / asinh(3), -1, 1 )
```

`s_x`／`s_y` 取 |rolling|／|momentum| 約 85 百分位。  
橫軸＝近5日淨流入；縱軸＝較前一窗動能；泡泡色依 `rolling_ret_5d`（**紅漲綠跌**）。

## 實作位置

| 層 | 路徑 |
|----|------|
| Python 純函式 | `etl/fundflo_model.py` |
| 測試 | `etl/test_fundflo_model.py` |
| 瀏覽器純函式 | `js/fundflo_model.js` |
| ETL 輸出 | `etl/build_fundflo_features.py` → `data/fundflo/` |
| UI | `fund-flow.html`（消費 JSON + 共用 JS，頁面不重算公式） |

## JSON 輸出示例

```json
{
  "code": "2330",
  "name": "台積電",
  "foreign_flow_yi": 12.3,
  "etf_flow_yi": 0.4,
  "combined_flow_yi": 12.7,
  "rolling_foreign_5d_yi": 40.1,
  "momentum_foreign_5d_yi": 5.2,
  "rolling_combined_5d_yi": 41.0,
  "momentum_combined_5d_yi": 5.5,
  "rolling_ret_5d": 2.15,
  "shares": 1230000
}
```
