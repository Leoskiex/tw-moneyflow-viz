# Fugle 分K／歷史 K 線（5m 路徑）

> 2026-09-11 · AISTOCKMAP · CoS 交辦  
> FinMind 免費档**不能**做個股 5 分 OHLC；改走 Fugle Market Data。

## 契約

| | |
|--|--|
| 抓取 | `etl/fetch_fugle_candles.py` |
| 快取 | `data/candles/<code>_<tf>.json`（如 `2330_5m.json`），並 merge 進 `data/candles/<code>.json` 的 `timeframes` |
| UI | `stock.html?code=2330` 讀 cache；有 bar 才啟用 5m／15m／60m |
| Key | `FUGLE_API_KEY` → env 或 box-secrets `card.FUGLE_API_KEY`；Header `X-API-KEY` |
| **禁止** | key 進瀏覽器；寫入 FundFlo slim／`refresh_daily` |

## API

```
GET https://api.fugle.tw/marketdata/v1.0/stock/historical/candles/{symbol}
Header: X-API-KEY
Query: from, to  (區間 < 1 年), timeframe = 1|3|5|15|30|60|D|W|M
```

分鐘歷史自 2023-05-23 起（以官方為準）。WS streaming 本 spike **不做**。

## 怎麼跑

```bash
cd tw-moneyflow-viz
# 先有日線（FinMind）可選
python3 etl/fetch_finmind_candles.py --code 2330 --days 180

# Fugle 5／15／60 分＋日線
python3 etl/fetch_fugle_candles.py --code 2330 --timeframes 5,15,60,D --days 5

# 開頁
# https://…/stock.html?code=2330
# http://127.0.0.1:8777/stock.html?code=2330
```

## Rate／方案

煙測前未知；跑通後把 HTTP 狀態／額度錯誤記在本檔「煙測」一節。

## 與 FinMind

- 日線：FinMind 免費可用（fallback／主日線）。  
- 5m：只用 Fugle。不要把「每5秒統計」假扮成 5 分 K。

## 煙測（2026-09-11）

- Key：box-secrets `FUGLE_API_KEY`（env 可能尚未帶入舊 shell；fetcher 讀 secrets）
- `2330` `--timeframes 5,15,60,D --days 7`：
  - **5m** ok n=**324**（2026-09-04→09-11）
  - **15m** ok n=**114**
  - **1h** ok n=**30**
  - **1D** ok n=**6**
- 無 plan／rate 錯誤（HTTP 正常）
- UI：`stock.html` 讀 merge 後 `timeframes`／`2330_5m.json` 等啟用按鈕
