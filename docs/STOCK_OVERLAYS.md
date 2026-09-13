# STOCK_OVERLAYS — 疊加與 SEPA 規則（本機 JS，對齊 kansoku 檔案）

資料源：`data/candles/<code>.json`（FinMind 日K）、`data/candles/<code>_<tf>.json`（Fugle 分K）、`data/candles/0050.json`（加權指數，RS 基準）。
所有值由 OHLCV 本機計算；token 只在 shell env（`FINMIND_TOKEN`、`FUGLE_API_KEY`），不進瀏覽器。
對照的 kansoku 來源檔（只讀、復刻行為）：
1. `packages/core/src/analysis/sepa.ts` — `computeChecks()`（8 條）、`autoVerdict()`（PASS/WATCH 分層）、`computeEntryPlan()`（pivot×0.93 / +5% / T1 8% / T2 15%）
2. `packages/core/src/analysis/indicators.ts` — `sma()`、`ema()`、`macd()`、`rsSeries()`、`pyRound()`
3. `packages/core/src/analysis/zones.ts` — volume profile / 支撐區（本機先以 pivot 與 布林 近似）
4. `apps/web/src/features/charts/sepa/SepaDashboard.tsx` — 三 pane 版面（主圖 62% / RS 19% / 量能 19%）+ 圖名標籤
5. `apps/web/src/features/charts/sepa/SepaSidebar.tsx` — 右欄 key-value + 檢查表
6. `apps/web/src/features/charts/drawings/drawingsMachine.ts` 等 — 畫線模式機（level / trend / clear），本機存 `localStorage` key `kdw:<code>`

TW 換算（有記錄的偏離）：RS 基準用 **0050**（非 SPY）；MA 維持 kansoku 的 50/150/200（日K）。

## 1. stock.html 疊加
- MA5/20/60：SMA，算術平均，前 n-1 根無值。
- MACD(12/26/9)：EMA k=2/(n+1)，DIF=EMA12−EMA26，DEA=EMA9(DIF)，柱 = **2×(DIF−DEA)**
  （與 kansoku `indicators.ts` `macd()` 同式；2330 最後一根 DIF 16.0989 / DEA 14.0271 → hist +4.14）。
- RSI(14)：Wilder 平滑，AG=(AG·13+g)/14、AL=(AL·13+l)/14，RSI=100−100/(1+AG/AL)，AL=0 取 50。
- 樞軸（floor trader）：P=(H+L+C)/3，R1=2P−L，S1=2P−H，R2=P+(H−L)，S2=P−(H−L)。
- KD(9)：K=(C−LLV9)/(HHV9−LLV9)×100，D=K 的 9 根均值；平高取 50。
- 布林(20,2)：中=SMA20，上/下=中 ±2×總體標準差(20)。
- 情景欄（規則式，起點 34/33/33）：收盤 vs MA20 ±10；HIST 正負 ±8；RSI ≥55 / ≤45 / 中性 ±6；
  RSI>70 或 <30 各移 4 給基準；最後歸一到 100。

## 2. SEPA 8 檢查（sepa.ts `computeChecks()`）
以最後一根日K；MA 全為收盤 SMA；斜率用 21/84 根前的 200MA：
1. 價 > 150MA 且 > 200MA
2. 150MA > 200MA
3. 200MA 1月斜率 > 0（同時顯示 4 月）
4. 50MA > 150MA 且 > 200MA
5. 價 > 50MA（+≥25% 標記 ⚠ extended）
6. 距 52w 低 ≥ +30%（last ≥ low52×1.3）
7. 距 52w 高 ≤ 25% 內（last ≥ high52×0.75）
8. RS vs 0050：126日 excess ≥ 0 pp → pass；≥ −5 pp → unknown；否則 fail（無基準 → unknown）
   - excess pp = 個股漲% − 指數漲%（同一 lookback，以最近可用日對齊）；圖上畫 21/63/126 日三條。
52w 高/低取最近 min(252, n) 根的 high/low 極值。

## 3. 判定（sepa.ts `autoVerdict()`）
- 有任何 fail → FAIL：「8 條中 N 條 Fail (…) → 不滿足 SEPA 入場條件」。
- 全過且 (last/MA50−1) ≥ 25% → WATCH：已 extended，等回調至 50MA 附近新平台。
- 全過其餘 → WATCH：待目視確認整理形態；pivot ~ pivot+5% 且當日量 ≥ 1.5×20MA 量 → 可升 Strong Buy。

## 4. 進場計畫（sepa.ts `computeEntryPlan()`）
pivot = 最後收盤；stop = pivot×0.93；買進區上緣 = pivot×1.05；T1 = pivot×1.08、T2 = pivot×1.15；
RR = (T2−pivot)/(pivot−stop)，≥2 合格、≥3 佳。

## 5. 畫線（drawings）
- 模式：不畫 / 水平（點一次，記 price）/ 趨勢（點兩次，記 (time,price)×2）。
- 每碼獨立：`localStorage["kdw:<code>"] = [{type:'h',price}|{type:'t',a:[t,p],b:[t,p]}]`；「清除本碼」移除該 key。
- 繪於主圖上方的 canvas，坐標由 lightweight-charts 的 scalar/timeScale 換算。

## 6. 右欄 tabs
- 環境：`data/regime_latest.json`（日期、主/次環境、信心、外資淨額）。
- 消息：`data/candles/<code>_news.json`（FinMind `TaiwanStockNews` 標題，日期+標題，最多 10 條）。
- 情景：最後收盤、MA50/150/200、52w 高低、今日量能比、pass 數。
- 法人/ETF 水：`data/fundflo/latest.json` 只讀顯示日期（slim 不由本頁寫入）。

## 7. P3a — `stock.html`（兩項，對齊 sepa.ts / indicators.ts）
- A1：`macd()` 柱改 **2×(DIF−DEA)**，與 kansoku 同式（2330 最後一根 +4.14）。
- A2：`setMarkers`（僅 1D）復刻 `sepa.ts` `detectMarkers()`：
  climax top（量 ≥ 2.5×vol20MA 且為近 6 根局部高，紅 arrowDown）、跌破 MA50（橙）、跌破 MA200（紅）、
  52w 高（紫 square）；財報 `earnings` 因快取無日期清單 → 傳 `[]`（不佔號）。
  `index.html` 卡（`data-code`）、`fund-flow.html` 列（`.rank-item`）同形點擊進 `stock.html?code=`。

## 8. P3b — `sepa.html`
- B1：`dailyMarkers()` 同 A2 四類標記，畫在 SEPA 主 pane。
- B2：`supportZones()` 復刻 `zones.ts`：預設三層（MA50×0.98~1.02=watch；min(150,200)×0.97~max×1.03=value）
  + volume profile（近 120 根、30 bins、跨 bin 均攤、peak 擴充 @60% 權重、僅低點以下的 bin）；
  合併後依 low 降冪、中線 <0.85×last → value 否則 buy；另畫 POC。
- B3：「憑什麼」浮面板（右上、可關閉）：最後凍結點評全文 + 依數值生成的可追問句（rsi/hist/量比/法人/環境）。
- B4：`setInterval` 30s 輪詢 `data/candles/<code>_<tf>.json`（帶 `_=` 快取破口）；`visibilitychange` 回前台即補一輪；
  只比較各 `timeframes[tf].n`，有變才重繪。
- B5：畫線 `kdw:<code>`、AI 線 `kdw:<code>:ai`（由 jsonl 最後一筆 scenarios 生成紫虛線）；
  「清除本碼」只移本碼 key，「只清 AI 線」只移 `:ai` key；其他碼 key 不動。
- A5 Strong Buy：8 條全過 + 價在 pivot~pivot+5% 區間 + 當日量 ≥1.5×20MA → 升 'STRONG BUY'（綠）；2330 現況维持 WATCH。

## 9. §3 證據（computed on Mac, 2026-09-13, 8777 loopback）
- A1：2330 最後一根 DIF 16.2914 / DEA 14.3102 → hist = 2×(DIF−DEA) = **+3.9625**（js 式 seed）。
- A2 markers（2330，n=16）：末四筆 — 2026-08-24 跌破MA50、2026-09-02 跌破MA50、2026-06-23 52w高 square 2535；
  climax top 依 2.5×vol20 + 局部高；E 財报 = 無日期清單 → `[]`。
- A3 zones（last 2410）：MA50 關注區 2346.12–2441.88；長期價值區 1972.42–2260.88；
  POC 2380.00–2405.83；成交密集區 2328.33–2431.67（vp: lookback 120, bins 30, 60% 擴充）。
- A4：`setInterval` 30s + `_=` cache-bust；`visibilitychange` 補輪；4 頁 token grep = 0。
- A5：ext +0.67%、vol_ratio 1.0408(<1.5) → 2330 仍 FAIL(check 8)，Strong Buy 路徑 n/a。
- B3 命中率：凍結 backfill n=16 hits=11 = 68.8%；jsonl 現 n=2（as_of 2026-09-11 兩筆，+5 根未足 → 暫未計分）。
- B4 三問（全部由凍結欄位生成）：rsi14/hist/vol_ratio；foreign_flow_yi/combined_5d_yi；regime+信心 vs 0050。
- C1：index `.stock` 卡 code→stock.html?code= / name→sepa.html?code=；fund-flow 兩模板 rank-item 加 K線/SEPA 連結。
- C2：`data/etf/00981a/holdings_latest.json` date 2026-09-11，2330 權重 10.27%（台積電，amount 28,592,240,000 NTD）。
- Guards：token grep 0（4 頁）、longbridge grep 0、`git diff -- data/fundflo` 空、box crons paused。
- GitHub：main = b2eaf02（C1）、前置 8cbc86f（P3a/P3b）。

