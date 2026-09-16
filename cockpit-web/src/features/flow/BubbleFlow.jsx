import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { jget, DATA } from '../../lib/data.js';
import M from '../../lib/fundflo_model.js';

const BASE_MS = 4000;
const FINAL_HOLD_MS = 1600;
const PLAYBACK_DAYS = 30;

const fmtYi = (v) => (v == null || !Number.isFinite(v)) ? '—' : ((v >= 0 ? '+' : '') + v.toFixed(2) + ' 億');
const fmtYiPlain = (v) => (v == null || !Number.isFinite(v)) ? '—' : (v.toFixed(2) + ' 億');
const fmtPct = (v) => (v == null || !Number.isFinite(v)) ? '—' : ((v >= 0 ? '+' : '') + v.toFixed(2) + '%');
const cls = (v) => (v > 0 ? 'up' : v < 0 ? 'dn' : '');

const MODES = [
  { id: 'foreign', label: '外資' },
  { id: 'etf', label: '主動式ETF' },
  { id: 'combined', label: '綜合' },
  { id: 'turnover', label: '成交熱度' },
];

// Axis/quadrant copy per mode (verbatim from fund-flow.html syncAxisCopy).
function axisCopy(mode) {
  if (mode === 'turnover') {
    return {
      q1: '下跌・降溫', q2: '上漲・增溫', q3: '下跌・增溫', q4: '上漲・降溫',
      north: '當日股價上漲 ↑', west: '← 成交降溫', east: '成交增溫 →',
      riverNetK: '畫面成交合計', kDaily: '當日成交金額', kRoll: '前5日平均', kMom: '成交增溫',
    };
  }
  const tag = mode === 'etf' ? '主動式 ETF' : mode === 'combined' ? '外資＋主動式 ETF' : '外資';
  return {
    q1: '流出收斂', q2: '流入增強', q3: '流出擴大', q4: '流入放緩',
    north: '近5日淨額較前日增加 ↑', west: '← 近5日淨流出', east: '近5日淨流入 →',
    riverNetK: '畫面淨額合計', kDaily: '當日' + tag + '淨額', kRoll: '近5日累計', kMom: '較前一窗',
  };
}

// D9 — 四象限泡泡 (flow quadrant). Ported from :8777/fund-flow.html paintBubbles
// into the SPA (same AppSkeleton). Reads data/fundflo/series_top.json (same book as
// FundFlo rank). Topic/group labels come from the series rows (SoT-stamped) — no
// parallel topic map. Click bubble/name → /symbol/:code. No iframe, no kansoku.
export default function BubbleFlow() {
  const [series, setSeries] = useState(null);
  const [mode, setMode] = useState('foreign');
  const [dir, setDir] = useState('both');
  const [count, setCount] = useState(15);
  const [speed, setSpeed] = useState('1');
  const [frame, setFrame] = useState(null); // null = last
  const [playing, setPlaying] = useState(false);
  const [selected, setSelected] = useState(null);

  const stocks = useMemo(() => (series && series.series) || [], [series]);
  const daysLen = useMemo(() => (stocks[0] && stocks[0].days ? stocks[0].days.length : 0), [stocks]);
  const frameMax = Math.max(0, daysLen - 1 - M.WINDOW);
  const frameOffset = Math.max(0, frameMax - (PLAYBACK_DAYS - 1)); // last N frames
  const effMode = MODES.some(m => m.id === mode) ? mode : 'foreign';
  const heat = effMode === 'turnover';
  const copy = axisCopy(effMode);

  // playback engine (rAF) — mirrored from fund-flow.html tick()
  const stateRef = useRef({ frame: frameMax, last: 0, hold: 0 });
  const playingRef = useRef(false);
  useEffect(() => { stateRef.current.frame = frameMax; }, [frameMax]);
  useEffect(() => {
    if (frame == null) stateRef.current.frame = frameMax;
  }, [frame, frameMax]);

  useEffect(() => {
    let raf = 0;
    const tick = (now) => {
      const st = stateRef.current;
      const elapsed = Math.min(now - st.last, 150);
      st.last = now;
      if (playingRef.current && st.frame >= frameMax - 1e-6) {
        st.hold += elapsed;
        if (st.hold >= FINAL_HOLD_MS) { st.frame = 0; st.hold = 0; setFrame(0); }
      } else if (playingRef.current) {
        st.frame = Math.min(frameMax, st.frame + (elapsed * Number(speed)) / BASE_MS);
        setFrame(st.frame);
      }
      raf = requestAnimationFrame(tick);
    };
    if (playing) {
      playingRef.current = true;
      stateRef.current.last = performance.now();
      if (stateRef.current.frame >= frameMax - 1e-6) { stateRef.current.frame = 0; stateRef.current.hold = 0; setFrame(0); }
      raf = requestAnimationFrame(tick);
      return () => { playingRef.current = false; cancelAnimationFrame(raf); };
    }
    playingRef.current = false;
    return;
  }, [playing, frameMax, speed]);

  useEffect(() => {
    jget(DATA('data/fundflo/series_top.json')).then((d) => {
      setSeries(d);
      if (d) setTimeout(() => setPlaying(true), 500); // auto-demo, like fund-flow.html
    });
  }, []);

  if (!series) return <div className="flowbub"><div className="muted" style={{ padding: 16 }}>載入水流序列中…</div></div>;
  if (!stocks.length) return <div className="flowbub"><div className="muted" style={{ padding: 16 }}>尚無水流序列（series_top.json 空）</div></div>;

  const fIdx = Math.max(0, Math.min(frameMax, Math.floor((frame == null ? frameMax : frame) + 1e-6)));
  const absFrame = (local) => frameOffset + Math.max(0, Math.min(frameMax, Math.floor((local == null ? fIdx : local) + 1e-6)));
  const rows = M.ranked(stocks, absFrame(fIdx), count, effMode === 'turnover' ? 'turnover' : dir, effMode);

  // river totals (like paintRiver)
  let net = 0, mom = 0, nn = 0;
  for (const { state: st } of rows) {
    if (Number.isFinite(st.rolling)) { net += st.rolling; nn++; }
    if (heat) { if (Number.isFinite(st.turnoverChange)) mom += st.turnoverChange; }
    else if (Number.isFinite(st.momentum)) mom += st.momentum;
  }

  // scales + bubble geometry (interpolated positions, like paintBubbles)
  const t = (frame == null ? 0 : (frame - Math.floor(frame)));
  const sc = M.scales(rows.map(r => r.stock), effMode, [absFrame(fIdx), absFrame(Math.min(frameMax, fIdx + 1))].filter((v, i, a) => a.indexOf(v) === i));
  const unionSet = new Set(rows.map(r => r.stock.code));
  for (const r of M.ranked(stocks, absFrame(Math.min(frameMax, fIdx + 1)), count, effMode === 'turnover' ? 'turnover' : dir, effMode)) unionSet.add(r.stock.code);
  const bubbles = stocks.filter(s => unionSet.has(s.code)).map((stock) => {
    const a = M.state(stock, absFrame(fIdx), effMode);
    const b = M.state(stock, absFrame(Math.min(frameMax, fIdx + 1)), effMode);
    const st = M.interpolateState(a, b, t);
    if (!st || !Number.isFinite(st.rolling)) return null;
    const x = M.normalize((st.flow ?? st.rolling) || 0, sc.x);
    const y = M.normalize(st.momentum || 0, sc.y);
    const left = 50 + x * 42, top = 50 - y * 42;
    const size = 48 + Math.sqrt(Math.abs(st.rolling) / Math.max(sc.size, 1e-6)) * 56;
    const ret = st.rollingRet ?? st.rolling_ret;
    const color = (ret == null || ret >= 0) ? 'rgba(248,113,113,.82)' : 'rgba(34,197,94,.82)';
    return { code: stock.code, name: stock.name, topic: stock.topic, group: stock.group, st, left, top, size, color, ret };
  }).filter(Boolean);

  // detail stat for selected (like paintDetail)
  const sel = stocks.find(s => s.code === (selected || (rows[0] && rows[0].stock.code)));
  const selSt = sel ? M.state(sel, absFrame(), effMode) : null;
  const statOf = (id, v, isPct, plain) => ({ label: copy[id] || '', val: isPct ? fmtPct(v) : (plain ? fmtYiPlain(v) : fmtYi(v)), tone: (heat && !isPct && plain) ? '' : cls(v) });
  const stats = selSt ? (heat
    ? [statOf('kDaily', selSt.rolling, false, true), statOf('kRoll', selSt.average5, false, true), statOf('kMom', selSt.turnoverChange, true, false), { label: '近5日股價', val: fmtPct(selSt.rollingRet), tone: cls(selSt.rollingRet) }]
    : [statOf('kDaily', selSt.dailyFlow, false, false), statOf('kRoll', selSt.rolling, false, false), statOf('kMom', selSt.momentum, false, false), { label: '近5日股價', val: fmtPct(selSt.rollingRet), tone: cls(selSt.rollingRet) }]) : [];

  const sample = stocks[0];
  const endIdx = absFrame() + M.WINDOW;
  const dayDate = sample?.days?.[endIdx]?.date || '';
  const spanStart = sample?.days?.[absFrame(0) + M.WINDOW]?.date || '';
  const spanEnd = sample?.days?.[absFrame(frameMax) + M.WINDOW]?.date || '';
  const span = spanStart && spanEnd ? `${spanStart}～${spanEnd}` : '';

  return (
    <div className={'flowbub' + (heat ? ' heat' : '')}>
      <div className="fb-toolbar">
        <div className="fb-modes">
          {MODES.map(m => <button key={m.id} className={'mbtn' + (effMode === m.id ? ' on' : '')} onClick={() => { setMode(m.id); setDir('both'); }}>{m.label}</button>)}
        </div>
        <div className="fb-ctrl">
          <select value={effMode === 'turnover' ? 'turnover' : dir} aria-label="排行"
            onChange={e => setDir(e.target.value)}>
            {effMode === 'turnover'
              ? <><option value="turnover">成交金額</option><option value="surge">成交增溫</option></>
              : <><option value="both">兩邊都看</option><option value="buy">進來最多</option><option value="sell">出去最多</option></>}
          </select>
          <select value={count} aria-label="筆數" onChange={e => setCount(Number(e.target.value))}>
            {[10, 15, 20].map(n => <option key={n} value={n}>{n}</option>)}
          </select>
          <select value={speed} aria-label="速度" onChange={e => setSpeed(e.target.value)}>
            {['0.5', '1', '2', '3'].map(s => <option key={s} value={s}>{s}×</option>)}
          </select>
          <button className="fb-play" onClick={() => setPlaying(p => !p)}>{playing ? '⏸ 先停一下' : '▶ 讓水流動'}</button>
          <span className="fb-span muted">{span ? `回放最近${PLAYBACK_DAYS}日 ${span}` : ''}</span>
        </div>
      </div>

      <div className="fb-river">
        <div className="fb-card"><div className="k">{copy.riverNetK}</div><div className={'v' + cls(net)}>{heat ? fmtYiPlain(nn ? net : null) : fmtYi(nn ? net : null)}</div><div className="hint muted">{heat ? '排行檔的成交金額加總' : (net >= 0 ? '畫面裡整體水在進來' : '畫面裡整體水在出去')}</div></div>
        <div className="fb-card"><div className="k">今天比前一段</div><div className={'v ' + cls(mom)}>{heat ? fmtPct(nn ? mom / Math.max(nn, 1) : null) : fmtYi(nn ? mom : null)}</div><div className="hint muted">{heat ? '成交相對前5日平均' : '近5日窗相對前一窗'}</div></div>
        <div className="fb-card"><div className="k">這一天</div><div className="v">{dayDate || '—'}</div><div className="hint muted">拖時間軸看每天變</div></div>
      </div>

      <div className="fb-chart">
        <span className="quadrant q1">{copy.q1}</span>
        <span className="quadrant q2">{copy.q2}</span>
        <span className="quadrant q3">{copy.q3}</span>
        <span className="quadrant q4">{copy.q4}</span>
        <span className="axis north">{copy.north}</span>
        <span className="axis west">{copy.west}</span>
        <span className="axis east">{copy.east}</span>
        {bubbles.map(b => (
          <Link to={`/symbol/${b.code}`} key={b.code}
            className={'fb-bubble' + (sel && sel.code === b.code ? ' active' : '')}
            style={{ left: b.left + '%', top: b.top + '%', width: b.size + 'px', height: b.size + 'px', background: b.color }}
            title={`${b.code} ${b.name}${b.topic ? ' · ' + b.topic : ''}`}>
            <strong>{b.name}</strong>
            <span className="fb-ret">{fmtPct(b.ret)}</span>
            <span className="fb-val">{heat ? (Number.isFinite(b.st.rolling) ? b.st.rolling.toFixed(1) : '—') + '億' : ((b.st.rolling >= 0 ? '+' : '') + (Number.isFinite(b.st.rolling) ? b.st.rolling.toFixed(1) : '—'))}</span>
          </Link>
        ))}
      </div>

      <div className="fb-playback">
        <input type="range" min="0" max={String(frameMax)} step="0.01" value={frame == null ? frameMax : frame}
          aria-label="回放交易日"
          onChange={e => { setPlaying(false); setFrame(Number(e.target.value)); }} />
        <span className="fb-day">{dayDate || '—'}</span>
      </div>

      <div className="fb-detail">
        {stats.map((s, i) => <div className="fb-stat" key={i}><div className="k">{s.label}</div><div className={'v ' + s.tone}>{s.val}</div></div>)}
      </div>
      <div className="fb-legend muted">
        <span><i className="red" />紅＝近5日股價上漲</span><span><i className="green" />綠＝近5日股價下跌</span>
        <span>點泡泡進個股</span>
      </div>
    </div>
  );
}
