import { useEffect, useRef, useState } from 'react';
import * as LWC from 'lightweight-charts';
import { sma, macd, rsi, kd, boll, pivots, dailyMarkers, barsOf, n2 } from '../../lib/data.js';

// Center chart pane — candles + MA5/20/60 + vol, MACD (2× HIST), RSI/KD pane.
// Math is byte-ported from the working stock.html (docs/STOCK_OVERLAYS.md).
export default function ChartPanel({ code, doc, tf, overlays, p2stat, onOverlay, lastOverlay }) {
  const ref = useRef(null);
  const cRef = useRef(null);
  const ovRef = useRef(overlays);
  const tfRef = useRef(tf);
  ovRef.current = overlays;
  tfRef.current = tf;
  const [overlayOut, setOverlayOut] = useState({});

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.innerHTML = '';
    const mk = (h) => LWC.createChart(h, {
      layout: { background: { color: '#0e1620' }, textColor: '#8b9bb0' },
      grid: { vertLines: { color: '#1e293b' }, horzLines: { color: '#1e293b' } },
      rightPriceScale: { borderColor: '#243041' },
      timeScale: { borderColor: '#243041' },
    });
    const mainEl = document.createElement('div');
    const mEl = document.createElement('div');
    const rEl = document.createElement('div');
    mainEl.style.cssText = 'height:58%;width:100%';
    mEl.style.cssText = 'height:20%;width:100%';
    rEl.style.cssText = 'height:15%;width:100%';
    el.append(mainEl, mEl, rEl);

    const chart = mk(mainEl);
    const mChart = LWC.createChart(mEl, {
      layout: { background: { color: '#0e1620' }, textColor: '#8b9bb0' },
      grid: { visible: false }, rightPriceScale: { visible: false },
      timeScale: { borderColor: '#243041' },
    });
    const rChart = LWC.createChart(rEl, {
      layout: { background: { color: '#0e1620' }, textColor: '#8b9bb0' },
      grid: { visible: false }, rightPriceScale: { visible: false },
      timeScale: { borderColor: '#243041' },
    });
    const apply = () => {
      chart.applyOptions({ width: mainEl.clientWidth, height: mainEl.clientHeight });
      mChart.applyOptions({ width: mEl.clientWidth, height: mEl.clientHeight });
      rChart.applyOptions({ width: rEl.clientWidth, height: rEl.clientHeight });
    };
    apply();
    const ro = new ResizeObserver(apply);
    ro.observe(el);

    const series = chart.addCandlestickSeries({
      upColor: '#f87171', downColor: '#22c55e',
      borderUpColor: '#f87171', borderDownColor: '#22c55e',
      wickUpColor: '#f87171', wickDownColor: '#22c55e',
    });
    const vol = chart.addHistogramSeries({ priceFormat: { type: 'volume' }, priceScaleId: '', color: '#334155' });
    vol.applyOptions({ scaleMargins: { top: 0.8, bottom: 0 } });
    const maLine = (color, title) => chart.addLineSeries({ color, lineWidth: 1, title });
    const sMA5 = maLine('#f7c945', 'MA5'), sMA20 = maLine('#38bdf8', 'MA20'), sMA60 = maLine('#b98df7', 'MA60');
    const sK = maLine('#f7c945', 'K'), sD = maLine('#38bdf8', 'D');
    const sDIF = mChart.addLineSeries({ color: '#38bdf8', lineWidth: 1, title: 'DIF' });
    const sDEA = mChart.addLineSeries({ color: '#f7a345', lineWidth: 1, title: 'DEA' });
    const sHIST = mChart.addHistogramSeries({ lineWidth: 1, title: 'HIST (2×)' });
    const sRSI = rChart.addLineSeries({ color: '#38bdf8', lineWidth: 1, title: 'RSI14' });

    // user drawings (localStorage, purple lines — same as stock.html)
    const key = 'kdw:' + code;
    let drawnPrices = [];
    try { drawnPrices = JSON.parse(localStorage.getItem(key) || '[]'); } catch (_) { drawnPrices = []; }
    const drawn = drawnPrices.filter(p => p != null && isFinite(p))
      .map(p => ({ h: series.createPriceLine({ price: Math.round(p * 100) / 100, color: '#e879f9', title: '畫線', lineWidth: 1, lineStyle: 3 }), price: p }));

    let pivLines = [];
    const rebuildPivs = (bars) => {
      pivLines.forEach(l => series.removePriceLine(l.h));
      pivLines = [];
      if (ovRef.current.piv && bars.length && tfRef.current === '1D') {
        const p = pivots(bars[bars.length - 1]);
        [{ v: p.R2, c: '#f87171', t: 'R2' }, { v: p.R1, c: '#f87171', t: 'R1' },
          { v: p.P, c: '#f7c945', t: 'P' }, { v: p.S1, c: '#22c55e', t: 'S1' }, { v: p.S2, c: '#22c55e', t: 'S2' }
        ].forEach(l => pivLines.push({ h: series.createPriceLine({ price: Math.round(l.v * 100) / 100, color: l.c, title: l.t, lineWidth: 1, lineStyle: 2, axisLabelVisible: true }), price: l.v }));
      }
    };

    const push = (arr) => arr.filter(x => x && x.value != null);
    const setData = (bars) => {
      if (!bars.length) {
        series.setData([]); vol.setData([]); sMA5.setData([]); sMA20.setData([]); sMA60.setData([]);
        sDIF.setData([]); sDEA.setData([]); sHIST.setData([]); sRSI.setData([]); sK.setData([]); sD.setData([]);
        setOverlayOut({});
        return;
      }
      const T = bars.map(b => b.time), C = bars.map(b => b.close), V = bars.map(b => b.volume || 0);
      series.setData(bars.map(b => ({ time: b.time, open: b.open, high: b.high, low: b.low, close: b.close })));
      vol.setData(bars.map(b => ({ time: b.time, value: b.volume || 0, color: (b.close ?? 0) >= (b.open ?? 0) ? 'rgba(248,113,113,.35)' : 'rgba(34,197,94,.35)' })));
      const ma5 = sma(C, 5), ma20 = sma(C, 20), ma60 = sma(C, 60);
      sMA5.setData(ovRef.current.ma ? push(C.map((v, i) => ma5[i] != null ? { time: T[i], value: ma5[i] } : null)) : []);
      sMA20.setData(ovRef.current.ma ? push(C.map((v, i) => ma20[i] != null ? { time: T[i], value: ma20[i] } : null)) : []);
      sMA60.setData(ovRef.current.ma ? push(C.map((v, i) => ma60[i] != null ? { time: T[i], value: ma60[i] } : null)) : []);
      const mc = macd(C);
      sDIF.setData(push(C.map((v, i) => mc.dif[i] != null ? { time: T[i], value: mc.dif[i] } : null)));
      sDEA.setData(push(C.map((v, i) => mc.dea[i] != null ? { time: T[i], value: mc.dea[i] } : null)));
      sHIST.setData(ovRef.current.macd ? push(C.map((v, i) => mc.hist[i] != null ? { time: T[i], value: mc.hist[i], color: mc.hist[i] >= 0 ? 'rgba(248,113,113,.55)' : 'rgba(34,197,94,.55)' } : null)) : []);
      const rs = rsi(C, 14);
      sRSI.setData(ovRef.current.rsi ? push(C.map((v, i) => rs[i] != null ? { time: T[i], value: rs[i] } : null)) : []);
      if (ovRef.current.kd) {
        const k = kd(bars, 14);
        sK.setData(push(C.map((v, i) => k.K[i] != null ? { time: T[i], value: k.K[i] } : null)));
        sD.setData(push(C.map((v, i) => k.D[i] != null ? { time: T[i], value: k.D[i] } : null)));
      } else { sK.setData([]); sD.setData([]); }
      if (ovRef.current.mark && tfRef.current === '1D') series.setMarkers(dailyMarkers(bars).slice(-24));
      else series.setMarkers([]);
      rebuildPivs(bars);
      const i = C.length - 1;
      const vr20 = sma(V, 20)[i];
      const out = {
        close: C[i], MA20: n2(ma20[i]), MA50: n2(sma(C, 50)[i]),
        HIST: n2(mc.hist[i]), RSI14: n2(rs[i]),
        vol_ratio: vr20 ? n2(V[i] / vr20) : null,
      };
      setOverlayOut(out);
      if (onOverlay) onOverlay(out);
    };
    cRef.current = { chart, mChart, rChart, series, ro, setData, drawn };

    chart.subscribeClick((param) => {
      if (!ovRef.current.draw || !param || !param.point) return;
      let price = null;
      try { price = chart.coordinateToPrice(param.point.y, 'right'); } catch (_) {}
      if (price != null && isFinite(price)) {
        const p = Math.round(price * 100) / 100;
        drawn.push({ h: series.createPriceLine({ price: p, color: '#e879f9', title: '畫線', lineWidth: 1, lineStyle: 3 }), price: p });
        try { localStorage.setItem(key, JSON.stringify(drawn.map(d => d.price))); } catch (_) {}
      }
    });

    return () => { ro.disconnect(); chart.remove(); mChart.remove(); rChart.remove(); cRef.current = null; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code]);

  useEffect(() => {
    const c = cRef.current;
    if (!c) return;
    c.setData(barsOf(doc, tf));
  }, [doc, tf, overlays, code]);

  return (
    <div className="charts">
      <div className="chart-main" ref={ref} />
      <div className="chart-foot muted">
        {p2stat && <span className="pill" title="etl/cockpit_p2.py">{p2stat}</span>}
        {overlayOut.close != null && <span className="pill">收 {n2(overlayOut.close)}</span>}
      </div>
    </div>
  );
}
