# 台股主動 ETF 持股日揭抓取

AISTOCKMAP 路徑慣例（請維持）：

```
data/etf/<lowercase_code>/holdings/YYYY-MM-DD.json
data/etf/<lowercase_code>/holdings_latest.json
```

欄位對齊既有 00981A：

```json
{
  "date": "YYYY-MM-DD",
  "etf": "00981A",
  "fund_code": "49YTW|null",
  "source": "ezmoney|nomura_api|capital_api|taishin_html",
  "source_url": "...",
  "fetched_at": "...+08:00",
  "meta": {},
  "holdings": [
    {"code":"2330","name":"...","share":0,"amount":0,"weight_pct":0,"money_type":"NTD"}
  ]
}
```

## 瑤池金母

- **主線**：`00981A` 主動統一台股增長（經理人陳釧瑤／社群稱瑤池金母）
- 來源：ezMoney `FundCode=49YTW`，既有 `fetch_00981a.py`；batch CLI 亦走同一 ezMoney adapter
- jojoradar `stock_trend` 僅旁路，**非**持股來源
- 統一投信可日揭姊妹檔（瑤姐相關統一檔「全加入」；仍次於 00981A 主線，補強 `etf_flow_yi`）：
  - `00403A` → `63YTW`（enabled）
  - `00988A` → `61YTW`（enabled；全球股，ST 可能含海外代碼）
  - `00411A` → `64YTW`（enabled）
  - 以上皆次於 00981A 主線，只補強 etf_flow_yi

## Registry

實作：`/workspace/twse-trading/active_etf/registry.py`  
欄位：`code, name, issuer, source_kind, info_url|api_url, fund_code?, product_id?, holdings_path, cadence(daily|weekly|monthly), enabled, priority`

## 來源與方法

| code | 投信 | source_kind | URL / API | cadence | 狀態 |
|------|------|-------------|-----------|---------|------|
| 00981A | 統一 | ezmoney | https://www.ezmoney.com.tw/ETF/Fund/Info?FundCode=49YTW — `<div id="DataAsset" data-content>` HTML-escaped JSON；`AssetCode==ST` → Details | daily | OK（既有） |
| 00403A | 統一 | ezmoney | FundCode=63YTW 同上 | daily | OK |
| 00988A | 統一 | ezmoney | FundCode=61YTW 同上 | daily | OK（全球；equity filter 僅留數字代碼） |
| 00411A | 統一 | ezmoney | FundCode=64YTW 同上 | daily | OK |
| 00980A | 野村 | nomura_api | POST https://www.nomurafunds.com.tw/API/ETFAPI/api/Fund/GetFundAssets `{"FundID":"00980A","SearchDate":"YYYY-MM-DD"}` → TableTitle=股票 | daily | OK |
| 00985A | 野村 | nomura_api | 同上 FundID=00985A | daily | OK |
| 00999A | 野村 | nomura_api | 同上 FundID=00999A | daily | OK |
| 00982A | 群益 | capital_api | POST https://www.capitalfund.com.tw/CFWeb/api/etf/buyback `{"fundId":399}` → `data.stocks` | daily | OK |
| 00992A | 群益 | capital_api | 同上 `fundId`:500 | daily | OK |
| 00987A | 台新 | taishin_html | https://www.tsit.com.tw/ETF/Home/ETFSeriesDetail/00987A SSR 持股表 | daily? | 試抓；基準日欄位待確認（meta.todo） |

金額 `amount`：ezMoney 有原始市值；野村／群益以 `AUM/NAV × weight%` 估算並在 meta 標記；台新頁無市值則留 0（不造假）。

## CLI

```bash
cd /workspace/twse-trading
python3 fetch_active_etf_holdings.py --list
python3 fetch_active_etf_holdings.py
python3 fetch_active_etf_holdings.py --codes 00980A,00982A,00985A
```

單檔失敗只警告，不中止整批。

## Daily refresh

`refresh_daily.py` → `build_all()` 在 FundFlo 之前呼叫 `fetch_active_etf_holdings.run_batch()`（non-blocking）。  
00981A 成長主題雷達仍由 `build_00981a` 負責；其它檔只進 `etf_flow_yi`。

## FundFlo

`build_fundflo_features.load_etf_share_deltas()` 掃描 `data/etf/*/holdings/*.json`，對連續快照做 `share` 差分並加總到同一 `(date, code)`。
