# NVIDIA Watch Page — 從 nvidiascreener 學來的「觀察」頁

**As of:** 2026-09-16 · CoS Tasks · for Leoskie_L  
**參考（只學交互／資訊架構，不 vendor、不 iframe 當產品殼）：** https://nvidiascreener.streamlit.app/  
**產品名（參考站）：** NVIDIA Portfolio Tracker  
**本站落點：** SPA `:8778/watch`（頂欄新頁籤「觀察」）— **獨立頁**，不塞進 `/live` 或今日故事。

---

## 1. 參考站實際是什麼（已核對 UI）

**不是** 一般技術篩選器（RSI/MACD universe）。  
**是** NVIDIA **投資組合／13F 持股觀察艙**：

| 區塊 | 內容 |
|------|------|
| Sidebar | KOR／ENG；filters：`Current Holdings (13F)` · `Strategic Partnership` · `Exited`；Sort By（Investment 等）；Tag Guide；DATA＝Quotes（OPEN/CLOSED）via **Finnhub** |
| Timeline | 投資事件時間軸（例：SpaceX $21B stake、Naver $1B placement…） |
| Tabs | **Portfolio** · **Performance** · **Sectors** · **News** · **13F History** |
| Portfolio 表 | Company（名＋ticker＋tag＋產業／金額）· Price · Daily% · YTD% · Mkt Cap · P/E · Details |
| Performance | YTD 多線比價圖（legend 點選／雙擊獨顯） |
| Quotes | 盤中 Finnhub；收盤顯示 CLOSED |

樣本標的類型：公開股（MRVL、INTC、GLW…）＋非公開／特殊（SPCX、GENB）混在同一觀察名單。

**不做：** 複製 Streamlit 雲端、抄他們私有資料檔、把 Finnhub key 放前端。

---

## 2. 為何放進台股駕駛艙（角色）

| 問題 | 誰答 |
|------|------|
| 今天台股錢怎麼走 | `/` 今日（FundFlo） |
| 盤中台股要不要抬頭 | `/live` |
| **美股 AI／NVIDIA 生態這季誰在帳上、誰退出、相對表現** | **`/watch`（本頁）** |
| 這檔台股圖 | `/symbol/:code` |

對齊既有方向：USA+TW regime、SEC **13F**、不要另開第三個網站。  
觀察頁 = **美側 context 窗**；點到有台股對照的名字才 deep-link 回台股個股。

---

## 3. 本站設計（C7）

### 路由／殼

```text
AppSkeleton tabs:
今日 · 盤中 · 觀察 · 個股 · SEPA · 研究庫 · 助理 · 設置

/watch              → NVIDIA Portfolio Watch（預設）
/watch?tab=perf     → Performance（可選 query）
```

過渡：不要 iframe Streamlit（auth 轉圈、另一套 chrome）。可在設置放「開參考站」外鏈。

### UI（學參考、React 自研）

1. **左欄（窄）**  
   - 狀態 filter：持倉 13F／戰略夥伴／已退出（多選）  
   - Sort：Investment · YTD · Daily · Name  
   - Tag 圖例（展開）  
   - Quotes 狀態徽章（OPEN／CLOSED；來源標 Finnhub／fallback）

2. **上：Investment Timeline**  
   - 讀 `data/watch/nvidia/timeline.json`（手動／季度更新）

3. **中：五 tab**  
   - Portfolio 表（欄位對齊參考站）  
   - Performance：Lightweight Charts 或既有 chart lib，YTD % 多線  
   - Sectors：聚合條／餅（由 holdings.sector）  
   - News：`:8790` 代理新聞（Finnhub／FinMind 美股；無 key 則空態＋說明）  
   - 13F History：季度持倉表（`thirteen_f/*.json`）

4. **列點擊**  
   - 有 `tw_code` → `/symbol/:tw_code`  
   - 僅美股 → Details 抽屜（價／YTD／筆記）；不開 Kansoku／Longbridge

### 資料（Mac `data/`，金鑰僅 env）

```text
data/watch/nvidia/
  holdings.json      # master list + status + tags + investment_usd + sector + tw_code?
  timeline.json      # events
  thirteen_f/
    2024Q4.json …
  quotes_cache.json  # optional, written by helper
```

**`:8790` 新端點（建議）**

| Method | Path | 作用 |
|--------|------|------|
| GET | `/watch/nvidia` | 合併 holdings＋timeline＋cached quotes |
| GET | `/watch/quotes?tickers=` | Finnhub（`FINNHUB_API_KEY`）或 yfinance fallback；永不回傳 key |
| GET | `/watch/news?tickers=` | 可選 |

P0 可先 **靜態 JSON＋手動报价欄**；P1 再接 quotes。

### TW 對照（少量、明示）

| 美／敘事 | 可選 tw_code |
|----------|-------------|
| TSM / TSMC 敘事 | 2330 |
| 供應鏈敘事（自行維護註） | 2454、2303… |

沒有對照就不要硬連。

---

## 4. 檢查閘門 G-D7

- [ ] `:8778/watch` 200；頂欄有「觀察」；不整頁重載  
- [ ] Portfolio 可見 filter 後名單；Timeline 非空（seed 資料）  
- [ ] Performance 至少一條 YTD 線（有报价或 seed）  
- [ ] 前端 grep：FINNHUB／token／ghp_ = 0  
- [ ] 無 Streamlit iframe 當主殼；無 vendor 參考站程式碼  
- [ ] 有 `tw_code` 的列可進 `/symbol/:code`  
- [ ] 文件註明：本頁＝美 NVIDIA 生態觀察，≠ 台股 `/live`

---

## 5. 實作順序（接 master）

1. Seed `data/watch/nvidia/holdings.json`＋`timeline.json`（從公開 13F／新聞手工整理一版即可）  
2. SPA route `/watch`＋五 tab 殼（Quotes 可先 mock／cache）  
3. `:8790/watch/*` quotes（有 `FINNHUB_API_KEY` 才活）  
4. TW deep-link 欄  
5. （後）13F 季度 diff、News tab

**與 D1 關係：** 加頂欄一頁，不取代今日 FundFlo。  
**與 D3 熱力：** 不同——D3＝台股錢／题材格子；D7＝NVIDIA 組合觀察。

**本檔：** `docs/NVIDIA_WATCH_PAGE.md`
