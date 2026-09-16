// 今日故事 data layer — ports index.html (五章) + fund-flow.html (水流排行) into the SPA.
// Reads the SAME day-end JSON the story site reads (no second site, no LLM, no 5m).
// Unit gate: FundFlo `*_yi` = 億元 (see docs/FUNDFLO_CONTRACT.md). Never mix 千張/億.
import { jget, DATA } from './data.js';

// ---------- jargon → 白話 (verbatim pairs from index.html) ----------
export function plain(s) {
  let t = String(s ?? '');
  const pairs = [
    [/second_wave confirmation/gi, '洗盤後再往上的第二波'],
    [/second_wave/gi, '第二波'],
    [/fake_thrust/gi, '假動作'],
    [/mild_push/gi, '輕輕推'],
    [/exit_watch/gi, '退出觀察'],
    [/leverage_relay/gi, '借錢接力'],
    [/risk_off/gi, '大家都很怕'],
    [/inst_push/gi, '機構在推'],
    [/hot_money/gi, '熱錢很吵'],
    [/repair/gi, '市場在修復'],
    [/Confirmation/g, '確認那天'],
    [/Ignition/g, '第一下點火'],
    [/Day0/gi, '當天那一下'],
    [/regime/gi, '市場氣氛'],
    [/llm=false/gi, '不是機器人亂寫'],
    [/useful_as_falsifier/gi, '比較像提醒別被騙'],
    [/\bpp\b/g, '個百分點'],
    [/T\+1/g, '隔天再想'],
    [/focus/gi, '可跟名單'],
    [/caution/gi, '躲開名單'],
    [/NOW\/TRANSITION\/EDGE/g, '現在／變化／邊界'],
  ];
  for (const [a, b] of pairs) t = t.replace(a, b);
  return t;
}

export function stateClass(label) {
  const s = String(label || '');
  if (/推動|修復|偏多|接力/.test(s)) return 'good';
  if (/摩擦|壓力|風險|處置|注意/.test(s)) return 'warn';
  if (/撤退|出貨|很怕|避險/.test(s)) return 'bad';
  return 'neu';
}

// Load all story inputs in one shot (same files index.html fetches).
export async function loadStory() {
  const paths = {
    brief: 'data/regime_brief_latest.json',
    radar: 'data/action_radar_latest.json',
    playbooks: 'data/playbooks/playbook_v0.json',
    themes: 'data/theme_rotation/latest.json',
    scoreboard: 'data/scoreboard/latest.json',
    digest: 'data/digest_latest.json',
    streaks: 'data/flow_streaks_latest.json',
  };
  const out = {};
  await Promise.all(Object.entries(paths).map(async ([k, p]) => {
    out[k] = await jget(DATA(p));
  }));
  return out;
}

// ---------- 水流排行 (fund-flow.html rank, from data/fundflo/latest.json) ----------
// latest.json is a day-end slim: per-stock rolling/momentum/ret are pre-computed,
// so the rank reads those fields directly (no per-day `days` needed).
export const RANK_MODES = [
  { id: 'foreign', label: '外資', roll: 'rolling_foreign_5d_yi', mom: 'momentum_foreign_5d_yi', daily: 'foreign_flow_yi' },
  { id: 'combined', label: '綜合', roll: 'rolling_combined_5d_yi', mom: 'momentum_combined_5d_yi', daily: 'combined_flow_yi' },
  { id: 'etf', label: '主動式ETF', roll: 'rolling_etf_5d_yi', mom: 'momentum_etf_5d_yi', daily: 'etf_flow_yi' },
];

export function rankRows(stocks, modeId, direction, count) {
  const m = RANK_MODES.find(x => x.id === modeId) || RANK_MODES[0];
  let rows = (stocks || []).map(s => ({
    code: s.code, name: s.name,
    rolling: s[m.roll], momentum: s[m.mom], daily: s[m.daily],
    ret: s.rolling_ret_5d,
  })).filter(r => r.rolling != null || r.daily != null);
  const val = (r) => (r.rolling != null ? r.rolling : r.daily);
  if (direction === 'buy') rows = rows.filter(r => val(r) > 0).sort((a, b) => val(b) - val(a));
  else if (direction === 'sell') rows = rows.filter(r => val(r) < 0).sort((a, b) => val(a) - val(b));
  else rows = rows.slice().sort((a, b) => Math.abs(val(b)) - Math.abs(val(a)));
  return rows.slice(0, count);
}

// Whether a mode is actually populated in the slim (etf rolling is often absent).
export function modePopulated(stocks, modeId) {
  const m = RANK_MODES.find(x => x.id === modeId) || RANK_MODES[0];
  return (stocks || []).some(s => s[m.roll] != null);
}
