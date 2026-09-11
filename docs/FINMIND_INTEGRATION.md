# FinMind 整合邊界（AISTOCKMAP／FundFlo／clone）

> 2026-09-11 · 與 CoS 對齊後的契約。細節煙測見 `FINMIND_CANDLES.md`。

## 一句話

**日線＋籌碼用 FinMind 免費档當「個股鑽取衛星」；FundFlo／T86 日更主鏈不動；5 分 K 等 Sponsor。**

## 契約

| 層 | 路徑 | 規則 |
|----|------|------|
| Candle cache | `etl/fetch_finmind_candles.py` → `data/candles/<code>.json` | 共享契約；可夜間 watchlist；**不進** `refresh_daily`／FundFlo slim |
| UI | `stock.html?code=2330` | Lightweight Charts；深鏈自故事／雷達 |
| Token | box-secrets `FINMIND_TOKEN` | **只給 box／server 批次**；禁止放進瀏覽器 |
| Rate | Free／register ~600/hr | 積極快取；前端可繼續 anon CORS，勿共用我們的 token |

## 誰用什麼

| 消費者 | 用 FinMind？ | 怎麼用 |
|--------|--------------|--------|
| **tw-moneyflow-viz** | 是（衛星） | 日線 K；深鏈 `stock.html` |
| **FundFlo／T86 ETL** | 否（主鏈） | 法人／流仍以 TWSE T86＋curated；FinMind 最多交叉驗證並標來源 |
| **aistockmap-clone** | 已有瀏覽器直打 | `company.js`／`chips.js` 打 FinMind CORS；升級時優先改吃 Pages／candle／chips cache，live 當 fallback |
| **CMI** | 可選 join | T−1 融資／三大法人特徵；不擁有 FinMind ETL |

## 免費可用 vs 鎖定

| 資料 | 狀態 |
|------|------|
| `TaiwanStockPrice` 日線 | ✅ |
| 三大法人／融資融券／PER·PBR | ✅（clone chips 已用；可再快取） |
| `TaiwanStockKBar`／tick → 5m OHLC | ❌ Sponsor／Backer |
| 每5秒委託成交／加權5秒 | ✅ 但是**全市場／大盤**，**不能**合成個股 5 分 K |

## 本週／Backlog（AISTOCKMAP）

**本週：** 本文件；深鏈 `stock.html`；維持日線 spike。  
**Backlog：** clone `/c/[code]` tech tab 吃 cache；夜間 watchlist routine；chips cache；Sponsor 後 5m。

## 本地日更

日更主責仍是本地 agent（`FUNDFLO_FULL_HISTORY_HANDBOOK` rev3）。FinMind candle 批次是**另軌**，失敗不擋 T86 refresh。

## Watchlist batch (manual / later schedule)

```bash
# comma list
python3 etl/fetch_finmind_candles.py --codes 2330,2317,2454 --days 120 --sleep 1

# or file (see data/candles/watchlist.example.txt)
python3 etl/fetch_finmind_candles.py --watchlist data/candles/watchlist.example.txt --days 120
```

Writes each `data/candles/<code>.json` + summary `data/candles/latest.json`. **Do not** add to FundFlo `refresh_daily` slim.

## Fugle（5m 路徑）

FinMind 免費無法做個股 5 分 OHLC。分K改走 Fugle：見 `docs/FUGLE_CANDLES.md`。同樣 **server-only key → cache → stock.html**。
