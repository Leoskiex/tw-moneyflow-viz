# FinMind 個股 K 線鑽取（與 FundFlo 分離）

> Spike · 2026-09-11 · AISTOCKMAP · CoS 交辦

## 路徑

| 檔 | 用途 |
|----|------|
| `stock.html?code=2330` | Lightweight Charts 日線頁 |
| `etl/fetch_finmind_candles.py` | 拉 FinMind → `data/candles/<code>.json` |
| `data/candles/2330.json` | 快取（日線 bars） |
| `data/candles/latest.json` | 最近一次抓取摘要 |

**不要**接入 `refresh_daily.py`／FundFlo slim。

## 怎麼跑

```bash
cd tw-moneyflow-viz
# 日線（免費；可匿名，有 token 較高 rate limit）
python3 etl/fetch_finmind_candles.py --code 2330 --days 180

# 可選：分K（需 Sponsor 的 TaiwanStockKBar；免費會空）
python3 etl/fetch_finmind_candles.py --code 2330 --with-intraday

# 開頁（Pages 或本機 8777）
# https://…/stock.html?code=2330
# http://127.0.0.1:8777/stock.html?code=2330
```

Token：環境變數 `FINMIND_TOKEN` 或 box-secrets；可省略（匿名日線已驗證）。勿把方案說明文字貼進 token。

## 週期可用性（免費／$0 方案）

| TF | 資料集 | 免費方案 | 狀態 |
|----|--------|----------|------|
| **1D 日線** | `TaiwanStockPrice` | ✅ 在清單內 | **可用**（已煙測 2330） |
| 1m／5m／15m／1h／4h | `TaiwanStockKBar` 再重採樣 | ❌ 不在免費清單（Sponsor） | **禁用／升級後再做** |
| 盤感（非K線） | 每5秒委託成交統計等 | ✅ 在清單 | 可選後續，非本 spike |

## 煙測結果（2026-09-11）

- Auth：`anon`（假 token／方案文已拒絕）
- `2330` 日線：`status=200`，約 **124** 根（2026-03-16→2026-09-10），最後收盤 **2450**
- UI：紅漲綠跌 candlestick＋量能

## 阻擋

1. 真實 API token 尚未注入（用戶曾誤貼方案說明）；日線不依賴 token。  
2. 分K需 Sponsor。  
3. 生產 rate：匿名 ~300/hr；註冊 token ~600/hr。
