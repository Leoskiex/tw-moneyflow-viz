/**
 * MF_SAMPLE — EXAMPLE sample data only (NOT live TWSE).
 * Snapshot date: 2026-09-04
 * Topic / group membership from aistockmap TW_TOPIC_MEMBERS.json + ALL_TOPICS.csv.
 * Flow / KPI numbers remain invented EXAMPLE values; names & topic ids are real.
 */
window.MF_SAMPLE = {
  "meta": {
    "title": "台股籌碼資金流視覺化（範例）",
    "date": "2026-09-04",
    "note": "EXAMPLE sample data — 非即時證交所資料｜題材／產業對照來自 aistockmap TW topic map",
    "currency": "TWD",
    "unit_amount": "億元",
    "unit_share": "張",
    "topic_source": "aistockmap/topics/TW_TOPIC_MEMBERS.json + ALL_TOPICS.csv"
  },
  "market_kpi": {
    "foreign_net": 128.6,
    "trust_net": -42.3,
    "dealer_net": 18.7,
    "total_amount": 4520.8,
    "advance": 612,
    "decline": 428,
    "unchanged": 86,
    "margin_balance": 2856.4,
    "short_balance": 412.8
  },
  "history_kpi": [
    {"date": "2026-08-26", "foreign_net": 86.2, "trust_net": -12.5, "dealer_net": 5.1, "amount": 3980.0},
    {"date": "2026-08-27", "foreign_net": -45.8, "trust_net": 22.1, "dealer_net": -8.4, "amount": 4120.5},
    {"date": "2026-08-28", "foreign_net": 112.4, "trust_net": -8.6, "dealer_net": 15.2, "amount": 4355.2},
    {"date": "2026-08-29", "foreign_net": 58.3, "trust_net": 31.0, "dealer_net": -3.7, "amount": 4210.8},
    {"date": "2026-09-01", "foreign_net": -22.6, "trust_net": -55.4, "dealer_net": 9.8, "amount": 3890.1},
    {"date": "2026-09-02", "foreign_net": 95.7, "trust_net": 18.2, "dealer_net": -12.1, "amount": 4488.6},
    {"date": "2026-09-03", "foreign_net": 71.5, "trust_net": -28.9, "dealer_net": 6.4, "amount": 4312.3},
    {"date": "2026-09-04", "foreign_net": 128.6, "trust_net": -42.3, "dealer_net": 18.7, "amount": 4520.8}
  ],
  "topics": [
    {"id": "ai-server-odm", "name": "AI 伺服器｜整機組裝", "shortname": "AI 伺服器組裝", "group": "AI 伺服器", "companyCount": 12, "foreign_net": 77.5, "trust_net": -18.3, "dealer_net": 11.6, "amount": 1160.7, "vs20": 1.42},
    {"id": "container-shipping", "name": "運輸物流｜貨櫃航運", "shortname": "貨櫃航運", "group": "運輸物流", "companyCount": 11, "foreign_net": -5.2, "trust_net": -8.6, "dealer_net": 0.8, "amount": 112.6, "vs20": 0.78},
    {"id": "cowos-advanced-packaging", "name": "先進封測｜AI 先進封裝（CoWoS）", "shortname": "AI 先進封裝", "group": "先進封測", "companyCount": 10, "foreign_net": 6.8, "trust_net": -1.5, "dealer_net": 0.9, "amount": 88.2, "vs20": 1.28},
    {"id": "hpc-network-ic", "name": "IC 設計｜HPC 與網通 IC", "shortname": "HPC 與網通 IC", "group": "IC 設計", "companyCount": 14, "foreign_net": 8.4, "trust_net": -2.1, "dealer_net": 1.2, "amount": 210.8, "vs20": 1.15},
    {"id": "ic-substrate", "name": "基板材料｜IC 載板", "shortname": "IC 載板", "group": "基板材料", "companyCount": 10, "foreign_net": 15.6, "trust_net": -3.2, "dealer_net": 1.8, "amount": 145.7, "vs20": 1.35},
    {"id": "liquid_cooling_advanced", "name": "散熱冷卻｜液冷散熱系統", "shortname": "液冷散熱", "group": "散熱冷卻", "companyCount": 12, "foreign_net": 12.1, "trust_net": 2.4, "dealer_net": 1.5, "amount": 168.2, "vs20": 1.25},
    {"id": "niche-memory", "name": "記憶體｜NOR 與利基記憶體", "shortname": "利基記憶體", "group": "記憶體", "companyCount": 6, "foreign_net": -6.8, "trust_net": 4.2, "dealer_net": -1.1, "amount": 98.4, "vs20": 0.92},
    {"id": "wafer-foundry", "name": "半導體製造｜晶圓代工", "shortname": "晶圓代工", "group": "半導體製造", "companyCount": 5, "foreign_net": 53.7, "trust_net": -5.2, "dealer_net": 3.5, "amount": 1057.4, "vs20": 1.18}
  ],
  "groups": [
    {"name": "AI 伺服器", "topicCount": 5, "companyCount": 50, "change_pct": 3.24, "inst_net": 70.8, "amount_vs_20d": 1.5, "margin_delta": 16.6, "foreign_net": 77.5, "trust_net": -18.3, "dealer_net": 11.6, "vs20": 1.5, "amount": 1160.7},
    {"name": "IC 設計", "topicCount": 6, "companyCount": 79, "change_pct": 0.85, "inst_net": 7.5, "amount_vs_20d": 1.19, "margin_delta": -0.6, "foreign_net": 8.4, "trust_net": -2.1, "dealer_net": 1.2, "vs20": 1.19, "amount": 210.8},
    {"name": "傳產工業", "topicCount": 5, "companyCount": 78, "change_pct": 0.35, "inst_net": 4.2, "amount_vs_20d": 0.88, "margin_delta": 0.3, "foreign_net": 4.5, "trust_net": -1.2, "dealer_net": 0.9, "vs20": 0.88, "amount": 113.6},
    {"name": "先進封測", "topicCount": 5, "companyCount": 64, "change_pct": 0.95, "inst_net": 6.2, "amount_vs_20d": 1.18, "margin_delta": 0.4, "foreign_net": 6.8, "trust_net": -1.5, "dealer_net": 0.9, "vs20": 1.18, "amount": 88.2},
    {"name": "光學顯示", "topicCount": 3, "companyCount": 37, "change_pct": -0.55, "inst_net": -3.8, "amount_vs_20d": 0.82, "margin_delta": -0.6, "foreign_net": -4.1, "trust_net": 1.2, "dealer_net": -0.9, "vs20": 0.82, "amount": 110.4},
    {"name": "光通訊", "topicCount": 2, "companyCount": 38, "change_pct": 1.85, "inst_net": 18.6, "amount_vs_20d": 1.32, "margin_delta": 1.4, "foreign_net": 20.0, "trust_net": -5.7, "dealer_net": 4.3, "vs20": 1.32, "amount": 228.8},
    {"name": "半導體製造", "topicCount": 6, "companyCount": 58, "change_pct": 1.1, "inst_net": 52.0, "amount_vs_20d": 1.41, "margin_delta": 1.0, "foreign_net": 53.7, "trust_net": -5.2, "dealer_net": 3.5, "vs20": 1.41, "amount": 1057.4},
    {"name": "基板材料", "topicCount": 5, "companyCount": 40, "change_pct": 4.2, "inst_net": 14.2, "amount_vs_20d": 1.22, "margin_delta": 2.8, "foreign_net": 15.6, "trust_net": -3.2, "dealer_net": 1.8, "vs20": 1.22, "amount": 145.7},
    {"name": "散熱冷卻", "topicCount": 2, "companyCount": 25, "change_pct": 1.6, "inst_net": 16.0, "amount_vs_20d": 1.23, "margin_delta": 0.9, "foreign_net": 12.1, "trust_net": 2.4, "dealer_net": 1.5, "vs20": 1.23, "amount": 168.2},
    {"name": "智慧自動化", "topicCount": 5, "companyCount": 70, "change_pct": 0.95, "inst_net": 6.8, "amount_vs_20d": 1.08, "margin_delta": 0.5, "foreign_net": 7.4, "trust_net": -2.2, "dealer_net": 1.6, "vs20": 1.08, "amount": 134.4},
    {"name": "消費平台", "topicCount": 2, "companyCount": 25, "change_pct": -0.25, "inst_net": -1.2, "amount_vs_20d": 0.9, "margin_delta": -0.2, "foreign_net": -1.2, "trust_net": 0.3, "dealer_net": -0.3, "vs20": 0.9, "amount": 89.6},
    {"name": "消費終端", "topicCount": 4, "companyCount": 42, "change_pct": 0.65, "inst_net": 5.4, "amount_vs_20d": 1.05, "margin_delta": 0.8, "foreign_net": 5.9, "trust_net": -1.7, "dealer_net": 1.2, "vs20": 1.05, "amount": 123.2},
    {"name": "生技醫療", "topicCount": 3, "companyCount": 23, "change_pct": -0.9, "inst_net": -4.5, "amount_vs_20d": 0.75, "margin_delta": -0.9, "foreign_net": -4.8, "trust_net": 1.4, "dealer_net": -1.1, "vs20": 0.75, "amount": 116.0},
    {"name": "綠能環保", "topicCount": 7, "companyCount": 92, "change_pct": 1.1, "inst_net": 9.2, "amount_vs_20d": 1.12, "margin_delta": 0.7, "foreign_net": 9.8, "trust_net": -2.8, "dealer_net": 2.2, "vs20": 1.12, "amount": 153.6},
    {"name": "航太國防", "topicCount": 2, "companyCount": 44, "change_pct": 0.45, "inst_net": 2.1, "amount_vs_20d": 0.98, "margin_delta": 0.2, "foreign_net": 2.2, "trust_net": -0.6, "dealer_net": 0.5, "vs20": 0.98, "amount": 96.8},
    {"name": "被動元件", "topicCount": 4, "companyCount": 45, "change_pct": 0.8, "inst_net": 7.5, "amount_vs_20d": 1.18, "margin_delta": 1.1, "foreign_net": 8.1, "trust_net": -2.3, "dealer_net": 1.7, "vs20": 1.18, "amount": 140.0},
    {"name": "記憶體", "topicCount": 4, "companyCount": 40, "change_pct": -1.85, "inst_net": -3.7, "amount_vs_20d": 0.92, "margin_delta": -1.2, "foreign_net": -6.8, "trust_net": 4.2, "dealer_net": -1.1, "vs20": 0.92, "amount": 98.4},
    {"name": "軟體資安", "topicCount": 4, "companyCount": 44, "change_pct": 0.55, "inst_net": 3.3, "amount_vs_20d": 0.95, "margin_delta": 0.1, "foreign_net": 3.6, "trust_net": -1.1, "dealer_net": 0.8, "vs20": 0.95, "amount": 106.4},
    {"name": "運輸物流", "topicCount": 2, "companyCount": 19, "change_pct": -2.3, "inst_net": -13.0, "amount_vs_20d": 0.96, "margin_delta": -2.4, "foreign_net": -5.2, "trust_net": -8.6, "dealer_net": 0.8, "vs20": 0.96, "amount": 112.6},
    {"name": "醫療器材", "topicCount": 3, "companyCount": 23, "change_pct": -0.4, "inst_net": -2.0, "amount_vs_20d": 0.85, "margin_delta": -0.3, "foreign_net": -2.2, "trust_net": 0.6, "dealer_net": -0.4, "vs20": 0.85, "amount": 96.0},
    {"name": "金融保險", "topicCount": 1, "companyCount": 25, "change_pct": 0.25, "inst_net": 16.8, "amount_vs_20d": 0.95, "margin_delta": 0.4, "foreign_net": 18.2, "trust_net": -5.2, "dealer_net": 3.8, "vs20": 0.95, "amount": 214.4},
    {"name": "電子零組件", "topicCount": 9, "companyCount": 125, "change_pct": 1.45, "inst_net": 28.4, "amount_vs_20d": 1.28, "margin_delta": 2.2, "foreign_net": 30.5, "trust_net": -8.8, "dealer_net": 6.7, "vs20": 1.28, "amount": 307.2}
  ],
  "stocks": [
    {"code": "2330", "name": "台積電", "foreign_net": 58.2, "trust_net": -6.4, "dealer_net": 4.1, "margin_delta": 1.8, "margin_util": 0.42, "short_sell": 3200, "sbl_sell": 1800, "short_util": 0.28, "change": 1.25, "amount": 980.5, "topicId": "wafer-foundry", "topic": "晶圓代工", "topicName": "半導體製造｜晶圓代工", "group": "半導體製造"},
    {"code": "2317", "name": "鴻海", "foreign_net": 22.6, "trust_net": -4.2, "dealer_net": 3.5, "margin_delta": 3.2, "margin_util": 0.55, "short_sell": 8500, "sbl_sell": 4200, "short_util": 0.41, "change": 2.1, "amount": 420.3, "topicId": "ai-server-odm", "topic": "AI 伺服器組裝", "topicName": "AI 伺服器｜整機組裝", "group": "AI 伺服器"},
    {"code": "2454", "name": "聯發科", "foreign_net": 8.4, "trust_net": -2.1, "dealer_net": 1.2, "margin_delta": -0.6, "margin_util": 0.38, "short_sell": 2100, "sbl_sell": 900, "short_util": 0.22, "change": 0.85, "amount": 210.8, "topicId": "hpc-network-ic", "topic": "HPC 與網通 IC", "topicName": "IC 設計｜HPC 與網通 IC", "group": "IC 設計"},
    {"code": "2382", "name": "廣達", "foreign_net": 18.9, "trust_net": -5.8, "dealer_net": 2.8, "margin_delta": 4.5, "margin_util": 0.68, "short_sell": 6200, "sbl_sell": 3100, "short_util": 0.52, "change": 3.45, "amount": 285.6, "topicId": "ai-server-odm", "topic": "AI 伺服器組裝", "topicName": "AI 伺服器｜整機組裝", "group": "AI 伺服器"},
    {"code": "2308", "name": "台達電", "foreign_net": 12.1, "trust_net": 2.4, "dealer_net": 1.5, "margin_delta": 0.9, "margin_util": 0.35, "short_sell": 1500, "sbl_sell": 700, "short_util": 0.18, "change": 1.6, "amount": 168.2, "topicId": "liquid_cooling_advanced", "topic": "液冷散熱", "topicName": "散熱冷卻｜液冷散熱系統", "group": "散熱冷卻"},
    {"code": "3037", "name": "欣興", "foreign_net": 15.6, "trust_net": -3.2, "dealer_net": 1.8, "margin_delta": 2.8, "margin_util": 0.61, "short_sell": 4800, "sbl_sell": 2200, "short_util": 0.48, "change": 4.2, "amount": 145.7, "topicId": "ic-substrate", "topic": "IC 載板", "topicName": "基板材料｜IC 載板", "group": "基板材料"},
    {"code": "2344", "name": "華邦電", "foreign_net": -6.8, "trust_net": 4.2, "dealer_net": -1.1, "margin_delta": -1.2, "margin_util": 0.48, "short_sell": 5600, "sbl_sell": 2800, "short_util": 0.55, "change": -1.85, "amount": 98.4, "topicId": "niche-memory", "topic": "利基記憶體", "topicName": "記憶體｜NOR 與利基記憶體", "group": "記憶體"},
    {"code": "2603", "name": "長榮", "foreign_net": -5.2, "trust_net": -8.6, "dealer_net": 0.8, "margin_delta": -2.4, "margin_util": 0.52, "short_sell": 7200, "sbl_sell": 3500, "short_util": 0.62, "change": -2.3, "amount": 112.6, "topicId": "container-shipping", "topic": "貨櫃航運", "topicName": "運輸物流｜貨櫃航運", "group": "運輸物流"},
    {"code": "3231", "name": "緯創", "foreign_net": 14.2, "trust_net": -3.5, "dealer_net": 2.1, "margin_delta": 3.8, "margin_util": 0.72, "short_sell": 9100, "sbl_sell": 4800, "short_util": 0.58, "change": 2.95, "amount": 198.5, "topicId": "ai-server-odm", "topic": "AI 伺服器組裝", "topicName": "AI 伺服器｜整機組裝", "group": "AI 伺服器"},
    {"code": "6669", "name": "緯穎", "foreign_net": 21.8, "trust_net": -4.8, "dealer_net": 3.2, "margin_delta": 5.1, "margin_util": 0.78, "short_sell": 3800, "sbl_sell": 2100, "short_util": 0.45, "change": 5.1, "amount": 256.3, "topicId": "ai-server-odm", "topic": "AI 伺服器組裝", "topicName": "AI 伺服器｜整機組裝", "group": "AI 伺服器"},
    {"code": "3711", "name": "日月光投控", "foreign_net": 6.8, "trust_net": -1.5, "dealer_net": 0.9, "margin_delta": 0.4, "margin_util": 0.33, "short_sell": 1800, "sbl_sell": 650, "short_util": 0.19, "change": 0.95, "amount": 88.2, "topicId": "cowos-advanced-packaging", "topic": "AI 先進封裝", "topicName": "先進封測｜AI 先進封裝（CoWoS）", "group": "先進封測"},
    {"code": "2303", "name": "聯電", "foreign_net": -4.5, "trust_net": 1.2, "dealer_net": -0.6, "margin_delta": -0.8, "margin_util": 0.44, "short_sell": 4500, "sbl_sell": 1900, "short_util": 0.36, "change": -0.75, "amount": 76.9, "topicId": "wafer-foundry", "topic": "晶圓代工", "topicName": "半導體製造｜晶圓代工", "group": "半導體製造"}
  ],
  "sectors": [
    {"name": "AI 伺服器", "topicCount": 5, "companyCount": 50, "change_pct": 3.24, "inst_net": 70.8, "amount_vs_20d": 1.5, "margin_delta": 16.6, "foreign_net": 77.5, "trust_net": -18.3, "dealer_net": 11.6, "vs20": 1.5, "amount": 1160.7},
    {"name": "IC 設計", "topicCount": 6, "companyCount": 79, "change_pct": 0.85, "inst_net": 7.5, "amount_vs_20d": 1.19, "margin_delta": -0.6, "foreign_net": 8.4, "trust_net": -2.1, "dealer_net": 1.2, "vs20": 1.19, "amount": 210.8},
    {"name": "傳產工業", "topicCount": 5, "companyCount": 78, "change_pct": 0.35, "inst_net": 4.2, "amount_vs_20d": 0.88, "margin_delta": 0.3, "foreign_net": 4.5, "trust_net": -1.2, "dealer_net": 0.9, "vs20": 0.88, "amount": 113.6},
    {"name": "先進封測", "topicCount": 5, "companyCount": 64, "change_pct": 0.95, "inst_net": 6.2, "amount_vs_20d": 1.18, "margin_delta": 0.4, "foreign_net": 6.8, "trust_net": -1.5, "dealer_net": 0.9, "vs20": 1.18, "amount": 88.2},
    {"name": "光學顯示", "topicCount": 3, "companyCount": 37, "change_pct": -0.55, "inst_net": -3.8, "amount_vs_20d": 0.82, "margin_delta": -0.6, "foreign_net": -4.1, "trust_net": 1.2, "dealer_net": -0.9, "vs20": 0.82, "amount": 110.4},
    {"name": "光通訊", "topicCount": 2, "companyCount": 38, "change_pct": 1.85, "inst_net": 18.6, "amount_vs_20d": 1.32, "margin_delta": 1.4, "foreign_net": 20.0, "trust_net": -5.7, "dealer_net": 4.3, "vs20": 1.32, "amount": 228.8},
    {"name": "半導體製造", "topicCount": 6, "companyCount": 58, "change_pct": 1.1, "inst_net": 52.0, "amount_vs_20d": 1.41, "margin_delta": 1.0, "foreign_net": 53.7, "trust_net": -5.2, "dealer_net": 3.5, "vs20": 1.41, "amount": 1057.4},
    {"name": "基板材料", "topicCount": 5, "companyCount": 40, "change_pct": 4.2, "inst_net": 14.2, "amount_vs_20d": 1.22, "margin_delta": 2.8, "foreign_net": 15.6, "trust_net": -3.2, "dealer_net": 1.8, "vs20": 1.22, "amount": 145.7},
    {"name": "散熱冷卻", "topicCount": 2, "companyCount": 25, "change_pct": 1.6, "inst_net": 16.0, "amount_vs_20d": 1.23, "margin_delta": 0.9, "foreign_net": 12.1, "trust_net": 2.4, "dealer_net": 1.5, "vs20": 1.23, "amount": 168.2},
    {"name": "智慧自動化", "topicCount": 5, "companyCount": 70, "change_pct": 0.95, "inst_net": 6.8, "amount_vs_20d": 1.08, "margin_delta": 0.5, "foreign_net": 7.4, "trust_net": -2.2, "dealer_net": 1.6, "vs20": 1.08, "amount": 134.4},
    {"name": "消費平台", "topicCount": 2, "companyCount": 25, "change_pct": -0.25, "inst_net": -1.2, "amount_vs_20d": 0.9, "margin_delta": -0.2, "foreign_net": -1.2, "trust_net": 0.3, "dealer_net": -0.3, "vs20": 0.9, "amount": 89.6},
    {"name": "消費終端", "topicCount": 4, "companyCount": 42, "change_pct": 0.65, "inst_net": 5.4, "amount_vs_20d": 1.05, "margin_delta": 0.8, "foreign_net": 5.9, "trust_net": -1.7, "dealer_net": 1.2, "vs20": 1.05, "amount": 123.2},
    {"name": "生技醫療", "topicCount": 3, "companyCount": 23, "change_pct": -0.9, "inst_net": -4.5, "amount_vs_20d": 0.75, "margin_delta": -0.9, "foreign_net": -4.8, "trust_net": 1.4, "dealer_net": -1.1, "vs20": 0.75, "amount": 116.0},
    {"name": "綠能環保", "topicCount": 7, "companyCount": 92, "change_pct": 1.1, "inst_net": 9.2, "amount_vs_20d": 1.12, "margin_delta": 0.7, "foreign_net": 9.8, "trust_net": -2.8, "dealer_net": 2.2, "vs20": 1.12, "amount": 153.6},
    {"name": "航太國防", "topicCount": 2, "companyCount": 44, "change_pct": 0.45, "inst_net": 2.1, "amount_vs_20d": 0.98, "margin_delta": 0.2, "foreign_net": 2.2, "trust_net": -0.6, "dealer_net": 0.5, "vs20": 0.98, "amount": 96.8},
    {"name": "被動元件", "topicCount": 4, "companyCount": 45, "change_pct": 0.8, "inst_net": 7.5, "amount_vs_20d": 1.18, "margin_delta": 1.1, "foreign_net": 8.1, "trust_net": -2.3, "dealer_net": 1.7, "vs20": 1.18, "amount": 140.0},
    {"name": "記憶體", "topicCount": 4, "companyCount": 40, "change_pct": -1.85, "inst_net": -3.7, "amount_vs_20d": 0.92, "margin_delta": -1.2, "foreign_net": -6.8, "trust_net": 4.2, "dealer_net": -1.1, "vs20": 0.92, "amount": 98.4},
    {"name": "軟體資安", "topicCount": 4, "companyCount": 44, "change_pct": 0.55, "inst_net": 3.3, "amount_vs_20d": 0.95, "margin_delta": 0.1, "foreign_net": 3.6, "trust_net": -1.1, "dealer_net": 0.8, "vs20": 0.95, "amount": 106.4},
    {"name": "運輸物流", "topicCount": 2, "companyCount": 19, "change_pct": -2.3, "inst_net": -13.0, "amount_vs_20d": 0.96, "margin_delta": -2.4, "foreign_net": -5.2, "trust_net": -8.6, "dealer_net": 0.8, "vs20": 0.96, "amount": 112.6},
    {"name": "醫療器材", "topicCount": 3, "companyCount": 23, "change_pct": -0.4, "inst_net": -2.0, "amount_vs_20d": 0.85, "margin_delta": -0.3, "foreign_net": -2.2, "trust_net": 0.6, "dealer_net": -0.4, "vs20": 0.85, "amount": 96.0},
    {"name": "金融保險", "topicCount": 1, "companyCount": 25, "change_pct": 0.25, "inst_net": 16.8, "amount_vs_20d": 0.95, "margin_delta": 0.4, "foreign_net": 18.2, "trust_net": -5.2, "dealer_net": 3.8, "vs20": 0.95, "amount": 214.4},
    {"name": "電子零組件", "topicCount": 9, "companyCount": 125, "change_pct": 1.45, "inst_net": 28.4, "amount_vs_20d": 1.28, "margin_delta": 2.2, "foreign_net": 30.5, "trust_net": -8.8, "dealer_net": 6.7, "vs20": 1.28, "amount": 307.2}
  ],
  "alerts": [
    {"level": "高", "code": "6669", "name": "緯穎", "type": "融資急增", "message": "融資餘額三日累計大增，融資使用率 78%，注意追高風險｜題材：AI 伺服器組裝", "value": "+5.1 億"},
    {"level": "高", "code": "2603", "name": "長榮", "type": "空單壓力", "message": "融券＋借券賣出合計偏高，空單使用率 62%｜題材：貨櫃航運", "value": "空單利用率 62%"},
    {"level": "中", "code": "2382", "name": "廣達", "type": "外資連買", "message": "外資五日淨買超累計偏強，題材：AI 伺服器組裝", "value": "+18.9 億"},
    {"level": "中", "code": "3037", "name": "欣興", "type": "漲幅＋融資", "message": "漲幅 4.2% 且融資同步增加，短線波動加大｜題材：IC 載板", "value": "+4.2% / 融資+2.8億"},
    {"level": "低", "code": "2344", "name": "華邦電", "type": "外資賣超", "message": "外資淨賣超，利基記憶體族群相對弱勢", "value": "-6.8 億"},
    {"level": "低", "code": "3231", "name": "緯創", "type": "槓桿偏高", "message": "融資使用率 72%，散佈圖落在高槓桿區｜題材：AI 伺服器組裝", "value": "融資利用率 72%"}
  ]
};
