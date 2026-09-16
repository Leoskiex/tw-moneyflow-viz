# 總設計＋檢查閘門 — 台股單一入口（整合一切已談事項）

**As of:** 2026-09-16 12:09 TPE · CoS Tasks · for Leoskie_L  
**性質：** 設計與閘門（先寫清楚，再開工）。不是 coding agent 立刻實作指令。  
**一句話：** 一個網站入口看懂台股；FundFlo／SPA／Kansoku 形能力拼在同一殼；資料同、解讀分頁。

**依據文件（勿互相打架，以本檔為開工閘門總表）：**
- `ONE_SITE_PLAN.md` — 單一入口 IA／階段  
- `ONE_SITE_PUZZLE.md` — 三件拼圖角色  
- `FUNCTION_DATA_MATRIX.md` — 60 功能×資料×計算  
- `PRO_FEATURES_DERIVED.md` — Pro 六項推演（自研）  
- `NVIDIA_WATCH_PAGE.md` — C7／D7 觀察頁（NVIDIA 13F 形）  
- `TOPIC_TAXONOMY_SOT.md` — 題材／群組全站同一本（TW_TOPIC_MEMBERS）  
- `SPA_SHELL_CITATIONS.md` — 已對齊 Kansoku 公開面  
- `STOCK_OVERLAYS.md` / `FUNDFLO_CONTRACT.md` / `INTRADAY_LIVE_WATCH.md`

---

## 0. 產品定義

| 項 | 決定 |
|---|---|
| 產品 | **台股駕駛艙**（暫名） |
| 唯一入口 | `http://127.0.0.1:8778/`（LAN 同 IP） |
| 資料根 | `/Users/lin/Downloads/tw-moneyflow-viz/data/` |
| 本機 API | `:8790`（金鑰僅 Mac env） |
| 日終 ETL | Mac `refresh_daily`（AISTOCKMAP 線；box cron 維持 paused） |
| Kansoku.app | 選用美股桌，**不嵌**本站 |
| 不做 | Vendor kansoku／Longbridge 台股／解 pro.enc／金鑰進前端／寫髒 FundFlo slim |

**使用者打開後必能回答：**
1. 今天錢／氣氛怎麼了？（今日）  
2. 盤中要不要抬頭？（盤中）  
3. 這檔圖怎麼看？（個股）  
4. 符不符合模板？（SEPA）  
5. 憑什麼／我記過什麼？（研究／助理／復盤）

---

## 1. 資訊架構（一個殼）

```text
:8778 AppSkeleton（不整頁重載）
├── /              今日 = FundFlo 故事＋水流＋雷達＋Recap（C1）
├── /live          盤中事件（C4）
├── /watch         觀察 = NVIDIA 組合／13F（C7）← nvidiascreener 形
├── /symbol/:code  個股三欄（C2）
├── /symbol/sepa/:code  SEPA（C3）
├── /research      研究庫（C5）
├── /assistant     助理（C5）
├── /settings      薄設置
└── /train         （後）盲盤
```

搜尋框 → `/symbol/:code`。  
`:8777/*.html` → 過渡 redirect 到上表；最終不當入口。

---

## 2. 集群與資料（同 data、不同解讀）

| ID | 名稱 | 主資料 | 解讀問題 | SPA 位置 |
|----|------|--------|----------|----------|
| C1 | 日終金錢故事 | fundflo、streaks、regime、radar、digest、etf | 誰搬了錢 | `/` |
| C2 | 個股技術 | candles ± overlays；环境讀 FundFlo 列 | 這檔怎麼走 | `/symbol/:code` |
| C3 | SEPA | 同日K＋0050 | 能不能進 | `/sepa` |
| C4 | 盤中獵人 | Fugle 5m≤60、live jsonl | 要不要抬頭 | `/live`＋launchd |
| C5 | 憑據／AI | jsonl、research、memory、LLM | 憑什麼 | 右欄＋research＋assistant |
| C6 | 六層研究 | features/outcomes | 這種事之後怎樣 | **不當首屏** |
| C7 | NVIDIA 觀察 | `data/watch/nvidia`＋quotes API | 美 AI 生態誰在帳上 | `/watch` |
| X | 邊界 | CMI CSV；分点 blocked | — | 徽章／不寫入 |
| X01web | CMI 天氣（薄） | `DAY_OPERATOR_latest.json` + overlay last row | 今天要不要防守？ | `/` 今日 badge（D8） |

**單位閘門：** curated `foreign_net`＝千張；FundFlo `*_yi`＝億。混用＝FAIL。

---

## 3. 已落地（基線，閘門＝維持不回退）

| # | 能力 | 驗收 |
|---|------|------|
| B1 | SPA 殼＋路由 | `:8778` deep link 200＋assets 絕對路徑；TCC 安全 dist |
| B2 | 個股／SEPA／Live／研究／助理 | 單窗切頁無整頁重載 |
| B3 | `:8790` fetch/ask/p2/comments/reassess/explain/follow/history/recap/livescan | 抽樣 200 |
| B4 | Livewatch launchd | session 內可掃；分点文案 blocked |
| B5 | 前端 0 token | grep FINMIND/FUGLE/ghp_ = 0 |
| B6 | Citations | `SPA_SHELL_CITATIONS.md` 有對照 |

---

## 4. 待做設計包（本輪「全部談到的」）

### D1 — 單一入口整合（Phase A＋B）

> 排行進今日＝D1；**四象限泡泡圖**另開 **D9**（本輪 D1 未含）。

**設計：**
- A：書籤／ensure 預設 8778；8777→8778 redirect  
- B：把 index 五章＋fund-flow 排行 **遷入** SPA `/`（讀同一 JSON）  
- 名稱點擊 → `/symbol/:code`

**檢查閘門 G-D1：**
- [ ] 只記一個 URL 能到今日／盤中／個股／SEPA  
- [ ] `/` 可見水流或故事至少一主塊＋點名進個股  
- [ ] 不再需要開 `fund-flow.html` 才看得到排行  
- [ ] FundFlo slim `git diff -- data/fundflo` 空（本工作）

### D2 — SEPA 三圖時間軸同步

**設計：** 主圖／RS／量 三個 `createChart`；主圖 `subscribeVisibleLogicalRangeChange` → 另兩圖 `setVisibleLogicalRange`；反向訂閱防抖／防循環。

**檢查閘門 G-D2：**
- [ ] 縮放／平移主圖，RS＋量時間窗一致  
- [ ] 縮放 RS 或量，主圖跟隨（或文件註明「僅主圖驅動」並閘門測主→從）  
- [ ] `sepa.html` 與 SPA SEPA 頁若並存，兩邊都過或舊頁 redirect

### D3 — 台股「熱力」學交互不抄美股 SPY

**設計：** 學 Kansoku／AISTOCKMAP 的 **點格子進個股、顏色＝強弱／流入**；數據用 FundFlo rolling／题材／screens／產業聚合，**不用** Longbridge／SPY heatmap。

**檢查閘門 G-D3：**
- [ ] `/` 或子視圖有產業／資金熱力（或明確排程）  
- [ ] 點單元 → `/symbol/:code`  
- [ ] 文件註明與美股 heatmap 差異（台＝錢／题材，美＝指數板塊）

### D4 — Pro 推演自研（見 PRO_FEATURES_DERIVED）

| 優先 | 項 | 設計摘要 | 閘門 |
|------|----|----------|------|
| P0 | 自動跟踪留言 | follow 名單＋livescan 高嚴重度 → 寫 comment＋notify | 跟蹤 2454，人造／真實事件後 feed 多一則 tracker，圖可關 |
| P1 | 長期記憶 | `data/memory/user.json`＋`symbols/<code>.json` 注入 ask／P2 | 設一句偏好後／ask 請求帶上；可清除 |
| P2 | 深度研究 | `/research-deep` 六節模板＋進度 UI | 2454 產出 md，節內有欄位引用 |
| P3 | 研究庫刷新採納 | 提案 diff→採納寫回 | 一輪刷新可採納 |
| P4 | 盲盤／畫布 | `/train`；canvas 後做 | 可標 defer |

**總閘門 G-D4：** 無 kansoku-pro 檔進 repo；無 Longbridge。

### D5 — Kansoku 覆蓋誠實表（設計約束）

| 狀態 | 項 |
|------|-----|
| 已進／接近 | SPA 殼、個股、SEPA、指標、復盤、AI點評、跟單 strip、研究起草、助理、Live、Recap |
| 半套 | 設置、环境（無券商倉）、畫線、ChatDock、Follow 推播 |
| 不做 | Electron／Sparkle／⌘T⌘K、Longbridge 報價分点帳戶、Canvas 產品（先）、Trainer（先）、Command palette（先）、Onboarding／Pro 付費牆、US／SPY heatmap、vendor repo |

**Onboarding／Pro（他們有、我們不搬）：**  
- Onboarding＝Longbridge＋AI＋可選 Twitter＋Pro 步  
- Pro 付費牆六項＝跟踪／深研／研究庫 AI／長期記憶／盲盤／畫布 → 我們用 D4 **自研**，不做他們授權碼流程


### D7 — NVIDIA Watch 頁（學 nvidiascreener，自研）

**依據：** `NVIDIA_WATCH_PAGE.md`（參考 https://nvidiascreener.streamlit.app/ = Portfolio Tracker，非技術篩選器）。

**設計：**
- 頂欄新頁籤「觀察」→ `/watch`
- Sidebar filters：13F 持倉／戰略夥伴／已退出；Sort；Timeline；Tabs＝Portfolio／Performance／Sectors／News／13F History
- 資料：`data/watch/nvidia/*`；报价經 `:8790`（Finnhub env 或 fallback）；**禁止** Streamlit iframe 當殼、禁止 key 進前端
- 有 `tw_code` 才 deep-link `/symbol/:code`（美股細節用抽屜）

**檢查閘門 G-D7：** 見 `NVIDIA_WATCH_PAGE.md` §4。


### D8 — CMI 天氣進 SPA「今日」（網頁面，非研究站）

**設計：** 把既有 Mac CMI 產出接到 `:8778` 今日頁，**不是**另開 CMI 網站、也不是搬整份 Day Operator HTML。

- 讀取（只讀）：
  - `cmi_system_v1_5/outputs/DAY_OPERATOR_latest.json`（或經 `:8790` 代理／複製到 `data/cmi/day_operator_latest.json` 供 8778 靜態讀）
  - 可選：`data/cmi/regime_overlay_daily.csv` 最後一列（regime / foreign / adv）
- UI：今日 `/` 頂部 **CMI 天氣徽章** — `weather.mode`（NORMAL／DEFENSIVE／CRASH_DEFENSE／RE_ENTER 等）+ `as_of` 日期 + 一句 `headline`／`action`
- 點徽章 → 展開薄面板（cash_target、allow_new_entries、foreign_net_yi、adv_ratio）；**不要**嵌入 STRATEGY_BOOK／MCPT／FULLSPEC 表
- 禁止：前端算 soft_gate；寫回 FundFlo；金鑰進前端；iframe Day Operator HTML

**檢查閘門 G-D8：**
- [ ] `:8778/` 可見 CMI 天氣徽章且 as_of 與 Day Operator JSON 一致  
- [ ] 無 MCPT／STRATEGY_BOOK 整頁搬進 SPA  
- [ ] grep tokens 0；`data/fundflo` 無寫入  
- [ ] overlay／Day Op 資料缺時顯示空態，不崩頁  


### D9 — 錢怎麼流 · 四象限泡泡圖進 SPA（bubble flow）

**設計：** 把舊 `fund-flow.html` 的 **泡泡圖**（F03）搬進單一入口，不要再靠 `:8777/fund-flow.html`。

- 落點：SPA **今日 `/`** 子視圖「盤面／水流」，或路由 `/flow`（同一 AppSkeleton）
- 讀同一 `data/fundflo/latest.json` + `js/fundflo_model.js` 邏輯（rolling_5d／momentum／ret；modes foreign｜etf｜combined｜turnover）
- UI：四象限泡泡 + 模式切換 +（有 series 時）播放軸；點泡泡 → `/symbol/:code`
- **不要** iframe 舊 html；**不要**另開第二站
- D1 已有的水流**排行表**保留；本項補視覺泡泡

**檢查閘門 G-D9：**
- [ ] `:8778/` 或 `/flow` 可見泡泡圖（非空態／非僅排行）  
- [ ] 切 mode 泡泡重排；點泡泡進個股  
- [ ] `:8777/fund-flow.html` 不再是看泡泡的必要入口（redirect 到 SPA 對應視圖）  
- [ ] FundFlo slim 無寫入；前端 0 token  

### D6 — Pages／安全／營運

- Pages：日K須 strip `timeframes`；無 5m；無 helper  
- 金鑰：僅 env；grep 閘門  
- box cron：paused  
- CMI：只消費 CSV  
- 8778：SPA fallback＋Application Support dist（TCC）

**閘門 G-D6：** grep tokens 0；livescan／8778／8790 抽樣 200；launchd 8778 KeepAlive。

---

## 5. 總檢查閘門（開工／完工共用）

### 設計完成閘（本檔寫完即過）
- [x] 單一入口 IA 寫清  
- [x] C1–C6／X 與 FUNCTION_DATA_MATRIX 對齊  
- [x] D1–D9 待做包＋驗收條列（D7＝watch；D8＝CMI；D9＝bubble flow）  
- [x] Pro 推演與「無私有源碼」邊界寫清  
- [x] SEPA sync、熱力、刻意不做已入閘門表  

### 實作階段建議順序
1. **G-D1** 入口＋今日吞 FundFlo（體感「一個站」）  
2. **G-D2** SEPA 三圖同步（你已痛的 bug）  
3. **G-D4 P0** 自动跟踪留言（系統替你盯）  
4. **G-D4 P1–P2** 記憶＋深研  
5. **G-D7** NVIDIA `/watch` 觀察頁  
6. **G-D8** CMI 天氣徽章進今日  
7. **G-D9** 四象限泡泡圖進 SPA  
8. **G-D3** 台股熱力  
9. **G-D4 P3–P4**、Pages slim 按需  

### 每 PR／每段完工必跑
- [ ] 單一 URL 煙測路徑：`/` → 點名 → SEPA → Live → Research  
- [ ] `grep` tokens 0  
- [ ] `data/fundflo` 無寫入  
- [ ] 分点仍為 blocked 文案  
- [ ] （若動 SEPA）G-D2  
- [ ] （若動 live／follow）G-D4 P0  

---

## 6. 給使用者的拍板句

批准本檔為 **唯一開工總閘** 後，CoS 再拆 paste：
1. `ONE_SITE` Phase A＋B（D1）  
2. SEPA range sync（D2）  
3. Derived Pro P0–P2（D4）

**本檔路徑：** `docs/MASTER_DESIGN_AND_GATES.md`
