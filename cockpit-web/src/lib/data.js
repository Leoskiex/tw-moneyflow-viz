// TW data layer — mirrors the :8790 helper + static data/ tree.
// No keys here; the helper holds FINMIND/FUGLE env on the Mac.

// Same-origin: the :8778 server serves both the SPA and the data tree,
// so relative paths work from any host with no CORS. (Legacy :8777 fallback
// only if the SPA is somehow served from a different origin.)
export const HOST = location.hostname;
export const DATA = (p) => '/' + p; // absolute from origin root (works on any deep route)
export const HELPER = HOST ? `http://${HOST}:8790` : null;

async function raw(url) {
  try {
    const r = await fetch(url, { cache: 'no-store' });
    return r.ok ? await r.text() : null;
  } catch (_) { return null; }
}
export async function jget(url) {
  const t = await raw(url);
  if (t == null) return null;
  try { return JSON.parse(t); } catch (_) { return null; }
}
export async function jraw(url) { return raw(url); }

// ---------- helper :8790 ----------
export async function helperStatus(code) {
  if (!HELPER) return null;
  return jget(`${HELPER}/status?code=${encodeURIComponent(code)}`);
}
export async function helperEnsure(code) {
  if (!HELPER) return null;
  try {
    const r = await fetch(`${HELPER}/fetch`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, tfs: ['5', '15', '60'] }),
    });
    return r.status === 409 ? 'already-running' : r.ok ? 'started' : 'error';
  } catch (_) { return 'offline'; }
}
export async function helperAsk(code, question, ctx) {
  if (!HELPER) throw new Error('helper offline');
  const r = await fetch(`${HELPER}/ask`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ code, question, context: ctx }),
  });
  return r.json();
}
export async function helperP2(code) {
  if (!HELPER) return null;
  try {
    const r = await fetch(`${HELPER}/p2`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code }),
    });
    return r.json();
  } catch (_) { return { error: 'helper offline' }; }
}
export async function p2State(code) {
  if (!HELPER) return null;
  return jget(`${HELPER}/p2?code=${encodeURIComponent(code)}`);
}
// ---------- AI點評 feed (kansoku AiTab/aiFeed port) ----------
export async function comments(code, date) {
  if (!HELPER) return null;
  const q = date ? `&date=${encodeURIComponent(date)}` : '';
  return jget(`${HELPER}/comments?code=${encodeURIComponent(code)}${q}`);
}
export async function reassessStart(code, origin) {
  if (!HELPER) return { error: 'helper offline' };
  try {
    const r = await fetch(`${HELPER}/reassess`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, origin: origin || 'manual' }),
    });
    return r.json();
  } catch (_) { return { error: 'helper offline' }; }
}
export async function reassessStatus(code) {
  if (!HELPER) return null;
  return jget(`${HELPER}/reassess?code=${encodeURIComponent(code)}`);
}
export async function explain(code) {
  if (!HELPER) return { error: 'helper offline' };
  try {
    const r = await fetch(`${HELPER}/explain`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code }),
    });
    return r.json();
  } catch (_) { return { error: 'helper offline' }; }
}
export const STANCE_LABEL = { act_per_plan: '按計劃執行', wait_confirm: '等確認', no_action: '不構成動作' };
export const STANCE_TONE = { act_per_plan: 'up', wait_confirm: 'accent', no_action: 'muted' };
export const REASON_TEXT = {
  'already-running': '已有分析在跑',
  'already-running:': '已有分析在跑',
};
// ---------- 復盤 outcome history (#14) ----------
export async function historyRows(code) {
  if (!HELPER) return [];
  const d = await jget(`${HELPER}/history?code=${encodeURIComponent(code)}`);
  return (d && d.rows) || [];
}
// ---------- 盤面 復盤板 (#19 RecapBoard) ----------
export async function recapRows() {
  if (!HELPER) return [];
  const d = await jget(`${HELPER}/recap`);
  return (d && d.rows) || [];
}
// ---------- 跟單 (#13) ----------
export async function followGet(code) {
  if (!HELPER) return null;
  const d = await jget(`${HELPER}/follow?code=${encodeURIComponent(code)}`);
  return d && d.state;
}
export async function followSet(code, entry, target, stop) {
  if (!HELPER) return { error: 'helper offline' };
  try {
    const r = await fetch(`${HELPER}/follow`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, entry, target, stop }),
    });
    return r.json();
  } catch (_) { return { error: 'helper offline' }; }
}
export async function followCancel(code) {
  if (!HELPER) return { error: 'helper offline' };
  try {
    const r = await fetch(`${HELPER}/follow`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, cancel: true }),
    });
    return r.json();
  } catch (_) { return { error: 'helper offline' }; }
}
// ---------- 復盤·笔记 (#16, localStorage per symbol) ----------
export function noteGet(code) { return localStorage.getItem(`kdw:note:${code}`) || ''; }
export function noteSet(code, text) { localStorage.setItem(`kdw:note:${code}`, text); }
// ---------- 研究庫 AI 起草 / 保存 (#17) ----------
export async function researchDraft(code) {
  if (!HELPER) return { error: 'helper offline' };
  try {
    const r = await fetch(`${HELPER}/research-draft`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code }),
    });
    return r.json();
  } catch (_) { return { error: 'helper offline' }; }
}
export async function researchSave(code, markdown) {
  if (!HELPER) return { error: 'helper offline' };
  try {
    const r = await fetch(`${HELPER}/research-save`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, markdown }),
    });
    return r.json();
  } catch (_) { return { error: 'helper offline' }; }
}
// ---------- 報價條 (#22): latest 5m bar ----------
export async function quote5m(code) {
  const d = await jget(DATA(`data/candles/${code}_5m.json`));
  const bars = (d && d.timeframes && d.timeframes['5m'] && d.timeframes['5m'].bars) || [];
  return bars.length ? bars[bars.length - 1] : null;
}

// ---------- candles ----------
export async function loadDoc(code) {
  let doc = await jget(DATA(`data/candles/${code}.json`));
  if (!doc) return null;
  for (const lab of ['5m', '15m', '1h', '60m', '30m']) {
    if (doc.timeframes?.[lab]?.ok && doc.timeframes[lab].n) continue;
    const part = await jget(DATA(`data/candles/${code}_${lab}.json`));
    const block = part?.timeframes?.[lab];
    if (block?.ok && block.n) {
      doc.timeframes = doc.timeframes || {};
      doc.timeframes[lab] = block;
    }
  }
  return doc;
}
export function barsOf(doc, tf) {
  if (!doc) return [];
  if (tf === '1D') return doc.daily || [];
  const b = doc.timeframes?.[tf];
  return b && b.ok ? b.bars || [] : [];
}

// ---------- indicator math (verbatim from stock.html / docs/STOCK_OVERLAYS.md) ----------
export const n2 = (v) => (v == null || !isFinite(v)) ? null : Math.round(v * 100) / 100;
export function sma(arr, n) {
  const out = new Array(arr.length); let acc = 0;
  for (let i = 0; i < arr.length; i++) { acc += arr[i]; if (i >= n) acc -= arr[i - n]; if (i >= n - 1) out[i] = acc / n; }
  return out;
}
export function ema(arr, n) {
  const k = 2 / (n + 1); const out = new Array(arr.length); let e;
  for (let i = 0; i < arr.length; i++) { e = i ? arr[i] * k + e * (1 - k) : arr[i]; out[i] = e; }
  return out;
}
// MACD with 2× histogram (the house convention)
export function macd(closes) {
  const e12 = ema(closes, 12), e26 = ema(closes, 26);
  const dif = closes.map((_, i) => e12[i] - e26[i]);
  const dea = ema(dif, 9);
  const hist = dif.map((v, i) => v == null || dea[i] == null ? null : 2 * (v - dea[i]));
  return { dif, dea, hist };
}
export function rsi(closes, n) {
  const out = new Array(closes.length);
  let ag = 0, al = 0;
  for (let i = 1; i < closes.length; i++) {
    const d = closes[i] - closes[i - 1];
    const g = d > 0 ? d : 0, l = d < 0 ? -d : 0;
    if (i <= n) { ag += g; al += l; if (i === n) { ag /= n; al /= n; out[i] = al ? 100 - 100 / (1 + ag / al) : 50; } }
    else { ag = (ag * (n - 1) + g) / n; al = (al * (n - 1) + l) / n; out[i] = al ? 100 - 100 / (1 + ag / al) : 50; }
  }
  return out;
}
export function kd(bars, n) {
  const K = new Array(bars.length), D = new Array(bars.length);
  for (let i = 0; i < bars.length; i++) {
    const lo = Math.min(...bars.slice(Math.max(0, i - n + 1), i + 1).map(b => b.low));
    const hi = Math.max(...bars.slice(Math.max(0, i - n + 1), i + 1).map(b => b.high));
    K[i] = hi > lo ? (bars[i].close - lo) / (hi - lo) * 100 : 50;
    D[i] = i >= n - 1 ? K.slice(i - n + 1, i + 1).reduce((a, b) => a + b, 0) / n : K[i];
  }
  return { K, D };
}
export function boll(closes, n, mult) {
  const mid = sma(closes, n); const up = new Array(closes.length), lo = new Array(closes.length);
  for (let i = n - 1; i < closes.length; i++) {
    const win = closes.slice(i - n + 1, i + 1);
    const m = mid[i];
    const sd = Math.sqrt(win.reduce((a, v) => a + (v - m) * (v - m), 0) / n);
    up[i] = m + mult * sd; lo[i] = m - mult * sd;
  }
  return { mid, up, lo };
}
export function pivots(b) {
  const P = (b.high + b.low + b.close) / 3;
  return { P, R1: 2 * P - b.low, S1: 2 * P - b.high, R2: P + (b.high - b.low), S2: P - (b.high - b.low) };
}
export function dailyMarkers(bars) {
  const T = bars.map(b => b.time), C = bars.map(b => b.close), H = bars.map(b => b.high);
  const V = bars.map(b => b.volume || 0);
  const vol20 = sma(V, 20), ma50 = sma(C, 50), ma200 = sma(C, 200);
  const mk = [];
  for (let i = 20; i < C.length; i++) {
    const v20 = vol20[i];
    if (v20 && V[i] >= 2.5 * v20 && C[i] < bars[i].open) {
      const w = Math.max(...H.slice(Math.max(0, i - 5), i + 1));
      if (H[i] === w) mk.push({ time: T[i], position: 'aboveBar', color: '#d32f2f', shape: 'arrowDown', text: `climax top (${(V[i] / v20).toFixed(1)}×)` });
    }
  }
  for (let i = 1; i < C.length; i++) {
    const p = ma50[i - 1], c = ma50[i];
    if (p && c && C[i - 1] >= p && C[i] < c) mk.push({ time: T[i], position: 'belowBar', color: '#ff9800', shape: 'arrowDown', text: '跌破 MA50' });
    const p2 = ma200[i - 1], c2 = ma200[i];
    if (p2 && c2 && C[i - 1] >= p2 && C[i] < c2) mk.push({ time: T[i], position: 'belowBar', color: '#d32f2f', shape: 'arrowDown', text: '跌破 MA200' });
  }
  const win = Math.min(252, H.length), hi = Math.max(...H.slice(-win));
  const hiIdx = H.indexOf(hi);
  if (hiIdx >= 0) mk.push({ time: T[hiIdx], position: 'aboveBar', color: '#9c27b0', shape: 'square', text: `52w 高 ${hi}` });
  mk.sort((a, b) => (a.time < b.time ? -1 : 1));
  return mk;
}
// SEPA 8 checks — shape of computeChecks() in kansoku packages/core/src/analysis/sepa.ts
export function computeChecks(last, ma50, ma150, ma200, ma2001m, ma2004m, hi52, lo52, rs21, rs126) {
  const fmt = (x, d) => (x == null || !isFinite(x)) ? '—' : x.toFixed(d);
  const st = (p) => p ? 'pass' : 'fail';
  const c1 = last > ma150 && last > ma200;
  const c2 = ma150 > ma200;
  const s1 = ma2001m ? ((ma200 - ma2001m) / ma2001m) * 100 : 0;
  const s4 = ma2004m ? ((ma200 - ma2004m) / ma2004m) * 100 : 0;
  const c3 = s1 > 0;
  const c4 = ma50 > ma150 && ma50 > ma200;
  const c5 = last > ma50;
  const c6 = last >= lo52 * 1.3;
  const c7 = last >= hi52 * 0.75;
  let c8 = 'unknown';
  if (rs126 != null) { if (rs126 >= 0) c8 = 'pass'; else if (rs126 >= -5) c8 = 'unknown'; else c8 = 'fail'; }
  let ext = '';
  if (c5) { const e = (last / ma50 - 1) * 100; if (e >= 25) ext = ` ⚠ extended +${e.toFixed(1)}%`; }
  return [
    { label: '價 > 150MA 且 > 200MA', status: st(c1), val: `價 ${fmt(last, 0)} vs 150MA ${fmt(ma150, 1)} / 200MA ${fmt(ma200, 1)}` },
    { label: '150MA > 200MA', status: st(c2), val: c2 ? `${fmt(ma150, 1)} > ${fmt(ma200, 1)}` : `${fmt(ma150, 1)} ≤ ${fmt(ma200, 1)}` },
    { label: '200MA 上行 ≥ 1 月', status: st(c3), val: `1月斜率 ${fmt(s1, 2)}%, 4月 ${fmt(s4, 2)}%` },
    { label: '50MA > 150MA 且 > 200MA', status: st(c4), val: c4 ? `${fmt(ma50, 1)} > ${fmt(ma150, 1)} > ${fmt(ma200, 1)}` : `${fmt(ma50, 1)} / ${fmt(ma150, 1)} / ${fmt(ma200, 1)}` },
    { label: '價 > 50MA', status: st(c5), val: `價 ${fmt(last, 0)} vs 50MA ${fmt(ma50, 1)} (${fmt((last / ma50 - 1) * 100, 1)}%)${ext}` },
    { label: '距 52w 低 ≥ +30%', status: st(c6), val: `+${fmt((last / lo52 - 1) * 100, 0)}% (低 ${fmt(lo52, 0)})` },
    { label: '距 52w 高 ≤ 25% 內', status: st(c7), val: `${fmt((last / hi52 - 1) * 100, 2)}% (高 ${fmt(hi52, 0)})` },
    { label: 'RS ≥ 0 pp (vs 0050)', status: c8, val: rs126 != null ? `21天 ${fmt(rs21, 1)} pp, 126天 ${fmt(rs126, 1)} pp` : '無 0050 資料，未計算' },
  ];
}
export function autoVerdict(checks, last, ma50, volRatio) {
  const fmt = (x, d) => (x == null || !isFinite(x)) ? '—' : x.toFixed(d);
  const fails = checks.filter(c => c.status === 'fail');
  if (fails.length) return { tier: 'fail', label: 'FAIL', reason: `趨勢模板 8 條中 ${fails.length} 條 Fail（${fails.slice(0, 3).map(c => c.label).join('、')}${fails.length > 3 ? '…' : ''}）→ 不滿足 SEPA 入場條件。` };
  const ext = (last / ma50 - 1) * 100;
  if (ext >= 25) return { tier: 'watch', label: 'WATCH LIST', reason: `8 條全過，但距 50MA +${ext.toFixed(1)}% 已 extended（>25% 警戒）。等回調至 50MA 附近形成新整理平台再觀察。` };
  if (volRatio != null && volRatio >= 1.5) return { tier: 'strong', label: 'STRONG BUY', reason: `8 條全過；價在 pivot ~ +5% 區間，當日量 ${volRatio.toFixed(2)}× ≥ 1.5×20MA → 升為 Strong Buy。` };
  return { tier: 'watch', label: 'WATCH LIST', reason: '8 條全過，待目視確認整理形態（VCP / 杯柄 / 平台 / 旗形）。若價在 pivot ~ pivot+5% 且當日量 ≥ 1.5×20MA，可升 Strong Buy。' };
}
export function entryPlan(pivot) {
  const pyR = (x, d = 0) => Math.round(x * Math.pow(10, d)) / Math.pow(10, d);
  const stop = pyR(pivot * 0.93, 2), bh = pyR(pivot * 1.05, 2);
  const t1 = pyR(pivot * 1.08, 2), t2 = pyR(pivot * 1.15, 2);
  const rr = pivot > stop ? (t2 - pivot) / (pivot - stop) : 0;
  return { pivot: pyR(pivot, 2), buy_high: bh, stop, stop_pct: (stop / pivot - 1) * 100, t1, t2, rr };
}
export function volumeProfile(bars, lookback = 120, nBins = 30) {
  const pyR = (x, d = 4) => Math.round(x * 10 ** d) / 10 ** d;
  const seg = Math.min(lookback, bars.length);
  const hs = bars.slice(-seg).map(b => b.high), ls = bars.slice(-seg).map(b => b.low), vs = bars.slice(-seg).map(b => b.volume || 0);
  const lo = Math.min(...ls), hi = Math.max(...hs);
  if (hi <= lo) return { bins: [], max_weight: 0, lookback: seg };
  const width = (hi - lo) / nBins;
  const arr = new Array(nBins).fill(0);
  for (let i = 0; i < seg; i++) {
    let bLo = Math.trunc((ls[i] - lo) / width), bHi = Math.trunc((hs[i] - lo) / width);
    bLo = Math.max(0, Math.min(nBins - 1, bLo)); bHi = Math.max(0, Math.min(nBins - 1, bHi));
    const per = vs[i] / (bHi - bLo + 1);
    for (let b = bLo; b <= bHi; b++) arr[b] += per;
  }
  const maxW = Math.max(...arr) || 1;
  return { bins: arr.map((w, i) => ({ low: pyR(lo + i * width), high: pyR(lo + (i + 1) * width), weight: pyR(w, 2), pct: pyR(w / maxW) })), max_weight: pyR(maxW, 2), lookback: seg };
}
export function supportZones(C, ma50, ma150, ma200, vp) {
  const pyR = (x, d = 2) => Math.round(x * 10 ** d) / 10 ** d;
  const out = [], last = C[C.length - 1];
  if (ma50 && ma50 < last) out.push({ low: pyR(ma50 * 0.98), high: pyR(ma50 * 1.02), tier: 'watch', label: 'MA50 關注區' });
  if (ma200 && ma200 < last) out.push({ low: pyR(Math.min(ma200, ma150 || ma200) * 0.97), high: pyR(Math.max(ma200, ma150 || ma200) * 1.03), tier: 'value', label: '長期均線價值區' });
  const below = vp.bins.filter(b => b.high < last);
  if (below.length) {
    const top = below.reduce((a, b) => (b.weight > a.weight ? b : a), below[0]);
    const idx = below.indexOf(top), th = top.weight * 0.6;
    let lo = top.low, hi = top.high;
    for (let j = idx - 1; j >= 0; j--) { if (below[j].weight >= th) lo = below[j].low; else break; }
    for (let j = idx + 1; j < below.length; j++) { if (below[j].weight >= th) hi = below[j].high; else break; }
    out.push({ low: pyR(lo), high: pyR(hi), tier: ((hi + lo) / 2 < last * 0.85 ? 'value' : 'buy'), label: '成交密集區' });
  }
  out.sort((a, b) => b.low - a.low);
  return out;
}

// ---------- fundflo / jsonl / news ----------
let fundfloCache = null;
export async function getFundFlo() { fundfloCache ||= await jget(DATA('data/fundflo/latest.json')); return fundfloCache; }
export function fundRow(code, ff) {
  return ff ? (ff.stocks || []).find(x => x.code === code) || null : null;
}
export async function getJsonl() {
  const t = await jraw(DATA('data/cockpit/cockpit.jsonl'));
  if (!t) return [];
  const rows = [];
  for (const line of t.split('\n')) {
    if (!line.trim()) continue;
    try { rows.push(JSON.parse(line)); } catch (_) {}
  }
  return rows;
}
export async function getNews(code) {
  const d = await jget(DATA(`data/news/${code}.json`));
  return (d && d.items) || [];
}
// FinMind 日股新聞 (helper fetches, caches to data/news/<code>.json; 6h TTL)
export async function helperNews(code, refresh) {
  if (!HELPER) return { error: 'helper offline' };
  return jget(`${HELPER}/news?code=${encodeURIComponent(code)}${refresh ? '&refresh=1' : ''}`);
}
let etfCache = {};
export async function getEtf(code) {
  if (etfCache[code]) return etfCache[code];
  const d = await jget(DATA(`data/etf/${code.toLowerCase()}/latest.json`)) || await jget(DATA('data/etf/00981a/latest.json'));
  etfCache[code] = d;
  return d;
}
export async function getRegime() { return jget(DATA('data/regime_latest.json')); }

// ---------- research md ----------
export function mdToHtml(src) {
  if (!src) return '';
  const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const lines = src.replace(/\r/g, '').split('\n');
  let html = '', inTable = false, inUl = false, inOl = false;
  const closeLists = () => { if (inUl) { html += '</ul>'; inUl = false; } if (inOl) { html += '</ol>'; inOl = false; } };
  const closeTable = () => { if (inTable) { html += '</tbody></table>'; inTable = false; } };
  for (const line of lines) {
    if (/^\s*\|/.test(line)) {
      const cells = line.replace(/^\s*\|/, '').replace(/\|\s*$/, '').split('|').map(x => esc(x.trim()));
      if (cells.every(c => /^:?-{2,}:?$/.test(c))) { closeLists(); closeTable(); html += '<table><tbody>'; inTable = true; continue; }
      if (inTable) { html += '<tr>' + cells.map(c => `<td>${c.replace(/\*\*(.+?)\*\*/g, '$1')}</td>`).join('') + '</tr>'; continue; }
      closeLists(); html += `<table><tbody><tr>${cells.map(c => `<td>${esc(c)}</td>`).join('')}</tr></tbody></table>`; continue;
    }
    closeTable();
    if (/^#{1,4}\s/.test(line)) { closeLists(); const m = line.match(/^(#{1,4})\s*(.*)/); html += `<h${m[1].length}>${esc(m[2])}</h${m[1].length}>`; continue; }
    if (/^\s*[-*]\s+/.test(line)) { closeLists(); if (!inUl) { html += '<ul>'; inUl = true; } html += `<li>${esc(line.replace(/^\s*[-*]\s+/, ''))}</li>`; continue; }
    if (/^\s*\d+\.\s+/.test(line)) { closeLists(); if (!inOl) { html += '<ol>'; inOl = true; } html += `<li>${esc(line.replace(/^\s*\d+\.\s+/, ''))}</li>`; continue; }
    if (/^\s*---+\s*$/.test(line)) { closeLists(); html += '<hr/>'; continue; }
    closeLists();
    if (line.trim()) html += `<p>${esc(line).replace(/`([^`]+)`/g, '<code>$1</code>').replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')}</p>`;
  }
  closeLists(); closeTable();
  return html;
}

// ---------- WAVE 3 D4 P1: 長期記憶 (helper :8790 /memory, files data/memory/*) ----------
// No keys in the frontend; memory is plain user/symbol JSON persisted on the Mac.
export async function memoryGet(code) {
  if (!HELPER) return { user: null, symbol: null, present: false };
  const q = code ? `?code=${encodeURIComponent(code)}` : '';
  return jget(`${HELPER}/memory${q}`) || { user: null, symbol: null, present: false };
}
export async function memorySave(scope, data, code) {
  if (!HELPER) return { error: 'helper offline' };
  try {
    const r = await fetch(`${HELPER}/memory`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'save', scope, code: code || '', data }),
    });
    return r.json();
  } catch (_) { return { error: 'helper offline' }; }
}
export async function memoryClear(scope, code) {
  if (!HELPER) return { error: 'helper offline' };
  try {
    const r = await fetch(`${HELPER}/memory`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action: 'clear', scope, code: code || '' }),
    });
    return r.json();
  } catch (_) { return { error: 'helper offline' }; }
}

// ---------- WAVE 3 D4 P2: 深度研究 (helper :8790 /research-deep job + poll) ----------
export async function researchDeepStart(code) {
  if (!HELPER) return { error: 'helper offline' };
  try {
    const r = await fetch(`${HELPER}/research-deep`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code }),
    });
    return r.json();
  } catch (_) { return { error: 'helper offline' }; }
}
export async function researchDeepStatus(code) {
  if (!HELPER) return null;
  return jget(`${HELPER}/research-deep?code=${encodeURIComponent(code)}`);
}
export async function researchRead(code, deep) {
  if (!HELPER) return null;
  return jget(`${HELPER}/research-read?code=${encodeURIComponent(code)}&deep=${deep ? 1 : 0}`);
}

// ---------- WAVE 4 D4 P3: 研究庫刷新採納 (helper :8790 /research-refresh + /research-adopt) ----------
export async function researchRefreshStart(code, path) {
  if (!HELPER) return { error: 'helper offline' };
  try {
    const r = await fetch(`${HELPER}/research-refresh`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, path: path || '' }),
    });
    return r.json();
  } catch (_) { return { error: 'helper offline' }; }
}
export async function researchRefreshStatus(code) {
  if (!HELPER) return null;
  return jget(`${HELPER}/research-refresh?code=${encodeURIComponent(code)}`);
}
export async function researchProposals(code, file) {
  if (!HELPER) return { proposals: [], detail: null };
  const q = file ? `&file=${encodeURIComponent(file)}` : '';
  return jget(`${HELPER}/research-proposals?code=${encodeURIComponent(code)}${q}`) || { proposals: [], detail: null };
}
export async function researchAdopt(code, proposal, action) {
  if (!HELPER) return { error: 'helper offline' };
  try {
    const r = await fetch(`${HELPER}/research-adopt`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code, proposal, action }),
    });
    return r.json();
  } catch (_) { return { error: 'helper offline' }; }
}
export async function researchTimeline(code) {
  if (!HELPER) return { rows: [] };
  return jget(`${HELPER}/research-timeline?code=${encodeURIComponent(code)}`) || { rows: [] };
}
