# FundFlo／台股資金流 — 全歷史整理手冊（給本地 agent）

> 寫給要在 **Mac／本地／有 raw 的環境** 接手 **日更＋剩餘 backlog** 的 agent。  
> 日期基準：2026-09-11（Asia/Taipei）· **rev3 — 可接手**。  
> 相關：`docs/FUNDFLO_CONTRACT.md`、`docs/ACTIVE_ETF_HOLDINGS.md`、`docs/LOCAL_AGENT_HANDOFF.md`。

---

## 接手結論（先看這裡）

**可以接手。** 日更主鏈路與 FundFlo／主動 ETF／水流 UI 已可交給本地 agent 全權維運。

**不是「研究／歷史層 100% 做完」。** 下列仍是 backlog（不擋日更）：

| 仍欠 | 影響 | 優先 |
|------|------|------|
| `data/curated/index.json` 過期（約 122 天／2026-03 起） | 易誤判「只有三月」 | P1 順手修 |
| `data/screens/` 約自 2026-01（~166 天） | 篩網歷史短 | P2 |
| **2023** curated 級聯 | raw 有、整理無 | P3 可選 |
| lifecycle／tournament 舊「~60d／119」文案 | 誤解 | P2 |
| 部分新主動 ETF 持股日數仍短 | `etf_flow_yi` 偏稀 | 靠日更累積 |

**已就緒（rev3 實測）：**

- curated／regimes／features／outcomes／signals／lifecycle ≈ **651 日**（2024-01-02→2026-09-09）
- FundFlo `series_top` **`keep_dates=120`**；UI `PLAYBACK_DAYS=30`
- `fund-flow.html`：外資｜主動式ETF｜綜合｜成交熱度＋rAF 插值
- 主動 ETF：統一 00981A／00403A／00411A／00988A＋野村等；`etf_flow` 非零已可到約 **14** 檔（隨日更成長）
- 日更腳本：`twse-trading/refresh_daily.py`（含 active ETF batch → fundflo slim）
- Pages：`Leoskiex/tw-moneyflow-viz` main → https://leoskiex.github.io/tw-moneyflow-viz/
- Mac 8777：`/Users/lin/Downloads/tw-moneyflow-viz` · `http://127.0.0.1:8777/`

總交接細節（含 GitHub／坑）：**`docs/LOCAL_AGENT_HANDOFF.md`**。本檔專注 FundFlo＋日更 slim＋歷史補齊。

---

## 0. 「為什麼只有 30／40／60／120 天？」

| 層 | 現況 | 說明 |
|----|------|------|
| raw | ~951 日（2023-01-02→2026-09-10） | 已下載 |
| curated | ~651 日（2024-01-02→2026-09-09） | 未含 2023 |
| `series_top` | **`keep_dates=120`** | Pages 可接受體積（約 12–13MB） |
| 開檔動畫 | **`PLAYBACK_DAYS=30`** | 故意只自動播近月；拖軸看更長 |
| 舊說「60 天／三月」 | 短樣本／過期 index | 見 §9 |

---

## 1. 目錄地圖

```
twse-trading/
  raw/YYYY-MM-DD/
  refresh_daily.py              # 日更入口
  fetch_active_etf_holdings.py
  active_etf/
  build_curated.py / curate_range.py / build_regimes.py / …

tw-moneyflow-viz/
  data/curated/ …
  data/fundflo/latest.json
  data/fundflo/series_top.json   # keep_dates=120
  data/etf/<code>/holdings/
  etl/build_fundflo_features.py
  fund-flow.html
  docs/…
```

Mac 8777 複本常在 `/Users/lin/Downloads/tw-moneyflow-viz`；**若缺 etl／raw，重跑 FundFlo 請在完整樹上做完再 slim 拷回**。

---

## 2. 硬規則

1. 禁止對巨大 `raw/` 用 `Path.iterdir()`／無界 glob → 用 `ls`／日期列表。  
2. 單位：`foreign_net`＝千張；`*_yi`＝億元；`foreign_flow_yi = foreign_net * price / 100`。  
3. Git：`gh`／`git push`；**禁止**對話貼 `ghp_`。  
4. Pages **slim**（每次日更成功後都要推）：  
   - 必：`data/fundflo/latest.json`、`series_top.json`、`fund-flow.html`、`js/fundflo_model.js`  
   - 建議：`data/etf/**/holdings_latest.json`、變更過的 digest／screens latest／html  
   - 勿：全量 curated、features／outcomes bulk、全 `by_date/`  
5. **00981A 主線故事權重不改**；其它主動 ETF 只補強 `etf_flow_yi`。  
6. UI 繁中白話。

---

## 3. 每日更新（本地 agent 維運清單）

平日收盤後（台北）：

### 3.1 跑 ETL

```bash
cd /path/to/twse-trading
python3 refresh_daily.py
```

內部大致：fetch 當日 raw → curated → regimes／screens → **active ETF batch（非阻擋）** → **FundFlo slim**（`latest`＋`series_top`，`write_by_date=False`）→ `data/refresh_status.json`。

- 若 T86 未好（exit 2）：等 10–15 分再試一次。  
- 官方約 18:00（未含巨額）／20:00（含）；可對齊既有 18:30 主跑＋20:45 補跑。

### 3.2 日更成功後必驗

```text
raw/manifest.json latest_trade_day
  == refresh_status.trade_day
  == screens_latest.date
  == fundflo latest.meta.date（或合理落後說明）
```

`ok=true`；`data/fundflo/series_top.json` 的 `meta.keep_dates` 仍為 **120**。

### 3.3 出貨

1. **Mac 8777**：把更新檔拷進 `/Users/lin/Downloads/tw-moneyflow-viz/`（至少 fundflo＋html／js＋etf holdings_latest）；必要時跑 `ensure_8777.sh`。  
2. **GitHub Pages**：在 `tw-moneyflow-viz` 工作複本 commit＋`git push origin main`（slim 集合）。  
3. 硬刷新驗證：  
   - https://leoskiex.github.io/tw-moneyflow-viz/fund-flow.html  
   - http://127.0.0.1:8777/fund-flow.html  
4. 給用戶一行中文：trade_day／screens／00981A 或 active ETF／fundflo／ok。

> 歷史坑：只同步 Mac、忘了 Pages → **每次成功日更都要推 Pages**。  
> box routine 曾 `resource_exhausted` → 本地應能手動重跑 `refresh_daily.py`。

---

## 4. FundFlo 重建／拉長（非每日）

```bash
cd tw-moneyflow-viz
# keep_dates 預設應已是 120；勿改回 40，勿加 --max-dates
python3 etl/build_fundflo_features.py \
  --skip-by-date \
  --raw-dir /絕對路徑/twse-trading/raw
```

主動 ETF 細節：`docs/ACTIVE_ETF_HOLDINGS.md`。新檔需 **≥2 個持股日** 才有 share 差分。

---

## 5. 歷史 backlog（可排進本地，不擋日更）

1. **P1** 重寫 `data/curated/index.json`（ls 全日）。  
2. **P2** screens 對齊 curated 全曆重跑。  
3. **P2** 清 lifecycle／tournament 過期 caveat；必要時重跑驗證。  
4. **P3** `curate_range` 起始改 2023-01-01 → 級聯 features／regimes／FundFlo。  
5. 持續讓主動 ETF 日揭累積（差分變密）。

---

## 6. 已知坑（精簡）

| 坑 | 處理 |
|----|------|
| manifest 未前進 → curated 停舊日 | 對齊 latest_trade_day 再 curate |
| Path.iterdir on raw | 改 ls |
| `--max-dates` | 正式產物禁用 |
| Mac 缺 raw／etl | 完整樹重跑再 slim 拷 |
| CDN 慢 | 硬刷新 Pages |
| 禁止對話要 GitHub token | 用已登入 gh／git |

---

## 7. 分工（rev3）

| 角色 | 負責 |
|------|------|
| **本地 agent（你）** | **日更全流程**、Mac＋Pages slim、§5 backlog、手動救 routine 失敗 |
| **反向破解** | 主動 ETF 來源／adapter、fund-flow 視覺能力（已合 main；後續增檔可協作） |
| **AISTOCKMAP（box）** | 可協助 sync／文件；**日更主責轉本地後以本地為準** |

---

## 8. 一頁口語

> 可以交給本地 agent 做每天更新了：跑 refresh、驗日期、推 Mac 8777 和 GitHub Pages。  
> 水流開檔播約三十天、底下有一百二十天系列；主動 ETF 已多檔在抓。  
> 還沒做完的是：curated 索引修好、screens 補歷史、可選 2023——都不擋明天的日更。

---

## 9. 完成度快表（2026-09-11 rev3）

| 區塊 | 狀態 |
|------|------|
| 日更 refresh＋FundFlo slim＋active ETF batch | 可接手維運 |
| fund-flow 四頁籤＋rAF＋keep_dates=120 | 完成 |
| curated／六層 by_date 2024→今 | 完成 |
| Pages／8777 slim 路徑 | 完成（日更後記得推） |
| curated index／screens 全曆／2023 | **未完 · backlog** |

