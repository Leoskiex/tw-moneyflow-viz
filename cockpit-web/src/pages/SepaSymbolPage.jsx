import { useEffect, useRef, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import * as LWC from 'lightweight-charts';
import {
  loadDoc, fundRow, getFundFlo, getJsonl,
  sma, macd, rsi, computeChecks, autoVerdict, entryPlan, volumeProfile, supportZones, n2,
} from '../lib/data.js';
import { pushRecent } from '../lib/symbolStore.js';

// /symbol/sepa/:sym — SEPA dashboard (shape of kansoku features/charts/sepa/SepaSymbolPage.tsx,
// math from packages/core/src/analysis/{sepa,zones,indicators}.ts — ported from our sepa.html).
export default function SepaSymbolPage() {
  const { sym } = useParams();
  const code = (sym || '').toUpperCase();
  const [doc, setDoc] = useState(null);
  const [bench, setBench] = useState(null);
  const [err, setErr] = useState('');
  const [name, setName] = useState('');
  const [rows, setRows] = useState([]);
  const mainRef = useRef(null);
  const rsRef = useRef(null);

  useEffect(() => {
    let dead = false;
    (async () => {
      setErr(''); setDoc(null);
      if (code) pushRecent(code);
      const d = await loadDoc(code);
      if (dead) return;
      if (!d) { setErr(`尚無快取 data/candles/${code}.json`); return; }
      setDoc(d);
      const b = await loadDoc('0050');
      setBench(b);
      const ff = await getFundFlo();
      const fr = (ff?.stocks || []).find(x => x.code === code);
      setName(fr ? fr.name : '');
      setRows(await getJsonl());
    })();
    return () => { dead = true; };
  }, [code]);

  const C = (doc && doc.daily) || [];
  const closes = C.map(b => b.close);
  const last = closes[closes.length - 1];
  const ma50 = sma(closes, 50)[closes.length - 1];
  const ma150 = sma(closes, 150)[closes.length - 1];
  const ma200 = sma(closes, 200)[closes.length - 1];
  const ma200_1m = closes.length > 211 ? closes.slice(-211)[-121] : null; // ~1 month back on 1D
  const ma200_4m = closes.length > 841 ? closes.slice(-841)[-721] : null; // ~4 months back
  const hi52 = Math.max(...C.slice(-252).map(b => b.high));
  const lo52 = Math.min(...C.slice(-252).map(b => b.low));
  const bc = bench?.daily || [];
  let rs21 = null, rs126 = null;
  if (bc.length > 126 && closes.length > 126) {
    const n = Math.min(126, closes.length, bc.length);
    const s = closes.slice(-n), t = bc.slice(-n);
    const r1 = (s[s.length - 1] / s[s.length - 22] - 1) * 100 - (t[t.length - 1] / t[t.length - 22] - 1) * 100;
    rs21 = r1;
    rs126 = (s[s.length - 1] / s[0] - 1) * 100 - (t[t.length - 1] / t[0] - 1) * 100;
  }
  const V = C.map(b => b.volume || 0);
  const vol20 = sma(V, 20)[V.length - 1];
  const volRatio = vol20 ? V[V.length - 1] / vol20 : null;

  const checks = (last && ma50 && ma150 && ma200)
    ? computeChecks(last, ma50, ma150, ma200, ma200_1m, ma200_4m, hi52, lo52, rs21, rs126) : [];
  const verdict = checks.length ? autoVerdict(checks, last, ma50, volRatio) : null;
  const plan = last ? entryPlan(last) : null;
  const vp = C.length >= 30 ? volumeProfile(C) : { bins: [], max_weight: 0 };
  const zones = (ma50 && ma200 && last) ? supportZones(closes, ma50, ma150, ma200, vp) : [];

  const mine = rows.filter(r => r.code === code);
  const frozen = mine[mine.length - 1];

  // charts
  useEffect(() => {
    if (!doc || !mainRef.current || !rsRef.current) return;
    const el = mainRef.current, er = rsRef.current;
    el.innerHTML = ''; er.innerHTML = '';
    const mk = (h) => LWC.createChart(h, {
      layout: { background: { color: '#0e1620' }, textColor: '#8b9bb0' },
      grid: { vertLines: { color: '#1e293b' }, horzLines: { color: '#1e293b' } },
      rightPriceScale: { borderColor: '#243041' },
      timeScale: { borderColor: '#243041', timeVisible: false },
    });
    const m = document.createElement('div'); m.style.cssText = 'height:62%;width:100%';
    const v = document.createElement('div'); v.style.cssText = 'height:20%;width:100%';
    const r = document.createElement('div'); r.style.cssText = 'height:18%;width:100%';
    el.append(m, v, r); er.append(r);
    const cMain = mk(m), cVol = mk(v), cRs = mk(r);
    // D2: triple-chart time sync — subscribe visibleLogicalRange on main → set on
    // RS/vol (and vice-versa, guarded) so zoom/pan stays in lockstep.
    let syncing = false;
    const subs = [];
    const sync = (src, r) => {
      if (syncing || !r || !Number.isFinite(r.from) || !Number.isFinite(r.to)) return;
      syncing = true;
      try {
        [cMain, cVol, cRs].forEach(c => {
          if (c === src) return;
          try { c.timeScale().setVisibleLogicalRange({ from: r.from, to: r.to }); } catch (_) {}
        });
      } finally { syncing = false; }
    };
    for (const c of [cMain, cVol, cRs]) {
      try {
        const u = c.timeScale().subscribeVisibleLogicalRangeChange(r => sync(c, r));
        if (typeof u === 'function') subs.push(u);
      } catch (_) { /* LWC build without this API: no sync, still works standalone */ }
    }
    const fit = () => {
      cMain.applyOptions({ width: m.clientWidth, height: m.clientHeight });
      cVol.applyOptions({ width: v.clientWidth, height: v.clientHeight });
      cRs.applyOptions({ width: r.clientWidth, height: r.clientHeight });
    };
    fit();
    const ro = new ResizeObserver(fit); ro.observe(el);
    const s = cMain.addCandlestickSeries({ upColor: '#f87171', downColor: '#22c55e', borderUpColor: '#f87171', borderDownColor: '#22c55e', wickUpColor: '#f87171', wickDownColor: '#22c55e' });
    const ln = (color, title, w) => cMain.addLineSeries({ color, lineWidth: w || 1, title });
    const l50 = ln('#f7c945', 'MA50'), l150 = ln('#38bdf8', 'MA150'), l200 = ln('#b98df7', 'MA200');
    const vBar = cVol.addHistogramSeries({ color: '#334155', lineWidth: 1, title: 'vol/20MA' });
    const r21 = cRs.addLineSeries({ color: '#38bdf8', lineWidth: 1, title: 'RS 21d' });
    const r126 = cRs.addLineSeries({ color: '#f7a345', lineWidth: 1, title: 'RS 126d' });

    const bars = C;
    s.setData(bars.map(b => ({ time: b.time, open: b.open, high: b.high, low: b.low, close: b.close })));
    const cl = bars.map(b => b.close);
    const ma50s = sma(cl, 50), ma150s = sma(cl, 150), ma200s = sma(cl, 200);
    l50.setData(cl.map((x, i) => ma50s[i] != null ? { time: bars[i].time, value: ma50s[i] } : null).filter(Boolean));
    l150.setData(cl.map((x, i) => ma150s[i] != null ? { time: bars[i].time, value: ma150s[i] } : null).filter(Boolean));
    l200.setData(cl.map((x, i) => ma200s[i] != null ? { time: bars[i].time, value: ma200s[i] } : null).filter(Boolean));
    const vol20s = sma(bars.map(b => b.volume || 0), 20);
    vBar.setData(bars.map((b, i) => vol20s[i] ? { time: b.time, value: (b.volume || 0) / vol20s[i] } : null).filter(Boolean));
    // RS vs 0050
    const bc2 = bench?.daily || [];
    if (bc2.length > 22 && bars.length > 22) {
      const n = Math.min(bars.length, bc2.length);
      const a = bars.slice(-n).map(b => b.close), t = bc2.slice(-n).map(b => b.close);
      const T2 = bars.slice(-n).map(b => b.time);
      const calc = (w) => a.map((x, i) => i + 1 >= w ? ((x / a[i + 1 - w] - 1) * 100 - (t[t.length - 1] / t[i + 1 - w] - 1) * 100) : null);
      r21.setData(T2.map((t2, i) => { const v = calc(21)[i]; return v != null ? { time: t2, value: v } : null; }).filter(Boolean));
      r126.setData(T2.map((t2, i) => { const v = calc(126)[i]; return v != null ? { time: t2, value: v } : null; }).filter(Boolean));
    }
    // zone shading
    zones.forEach(z => {
      const color = z.tier === 'value' ? 'rgba(0,137,123,.25)' : z.tier === 'buy' ? 'rgba(38,166,154,.2)' : z.tier === 'watch' ? 'rgba(255,193,7,.15)' : 'rgba(239,83,80,.15)';
      s.createPriceLine({ price: z.high, color, lineStyle: 0, axisLabelVisible: false });
      s.createPriceLine({ price: z.low, color: '#8b9bb0', lineWidth: 1, lineStyle: 2, title: z.label, axisLabelVisible: true });
    });
    return () => { ro.disconnect(); subs.forEach(u => u.unsubscribe()); cMain.remove(); cVol.remove(); cRs.remove(); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [doc, bench]);

  if (!code) return <div className="page"><div className="err">請輸入代碼</div><Link to="/">← 返回列表</Link></div>;
  const tierColor = verdict?.tier === 'strong' ? 'var(--ok)' : verdict?.tier === 'watch' ? 'var(--warn)' : 'var(--down)';

  return (
    <div className="page sepa-page">
      <div className="sepa-head">
        <Link to="/" className="back">← 列表</Link>
        <span className="code">{code}</span><span className="nm">{name}</span>
        <Link to={`/symbol/${code}`} className="sepalink">← 個股駕駛艙</Link>
        {verdict && (
          <span className="pill" style={{ borderColor: tierColor, color: tierColor, fontWeight: 700 }}>{verdict.label}</span>
        )}
      </div>
      {err && <div className="err">{err}</div>}
      {!doc && !err && <div className="muted" style={{ padding: 20 }}>載入中…</div>}
      {doc && (
        <div className="sepa-grid">
          <div className="sepa-chart">
            <div className="lbl muted">主圖 · 日K + MA50/150/200 + 區間</div>
            <div ref={mainRef} className="cbox big" />
            <div className="lbl muted">RS vs 0050（跑贏百分點）</div>
            <div ref={rsRef} className="cbox" />
          </div>
          <div className="sepa-side">
            <div className="card">
              <h3>SEPA 8 條檢查（shape of sepa.ts computeChecks）</h3>
              <div className="checks">
                {checks.map((c, i) => (
                  <div key={i} className={'check ' + c.status}>
                    <span className="dot" /> {c.label}
                    <div className="muted">{c.val}</div>
                  </div>
                ))}
              </div>
              {verdict && <div className="verdict" style={{ color: tierColor }}>{verdict.reason}</div>}
            </div>
            {plan && (
              <div className="card">
                <h3>入場計劃（pivot=最後收盤）</h3>
                <div className="kv">
                  <div className="kvrow"><span>進場區</span><b>{plan.pivot} ~ {plan.buy_high}</b></div>
                  <div className="kvrow"><span>停損</span><b className="dn">{plan.stop}（{plan.stop_pct.toFixed(1)}%）</b></div>
                  <div className="kvrow"><span>目標 1/2</span><b>{plan.t1} / {plan.t2}</b></div>
                  <div className="kvrow"><span>R:R</span><b>{plan.rr.toFixed(2)}</b></div>
                </div>
              </div>
            )}
            {frozen && (
              <div className="card">
                <h3>凍結點評（cockpit.jsonl {frozen.as_of}）</h3>
                <div style={{ whiteSpace: 'pre-wrap', fontSize: 12 }}>{frozen.comment || '(無文字)'}</div>
              </div>
            )}
            {volRatio != null && (
              <div className="card">
                <h3>量能</h3>
                <div className="kv">
                  <div className="kvrow"><span>量比（vs 20MA）</span><b>{volRatio.toFixed(2)}×</b></div>
                  <div className="kvrow"><span>52w 高/低</span><b>{n2(hi52)} / {n2(lo52)}</b></div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
