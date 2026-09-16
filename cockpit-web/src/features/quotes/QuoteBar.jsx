import { useEffect, useState } from 'react';
import { quote5m, n2 } from '../../lib/data.js';
import FollowStrip from '../cockpit/FollowStrip.jsx';

// #22 報價條 (kansoku quotes/QuoteBar): live 5m last bar strip above the chart.
export default function QuoteBar({ code, doc, latestRow }) {
  const [q, setQ] = useState(null);
  const lastDaily = doc && doc.daily && doc.daily.length ? doc.daily[doc.daily.length - 1] : null;

  useEffect(() => {
    let live = true;
    (async () => { setQ(await quote5m(code)); })();
    const t = setInterval(async () => { if (live) setQ(await quote5m(code)); }, 60000);
    return () => { live = false; clearInterval(t); };
  }, [code]);

  const bar = q || lastDaily;
  if (!bar) return null;
  const prev = q && doc ? (doc.timeframes?.['5m']?.bars || [])[ (doc.timeframes['5m'].bars.length || 1) - 2 ]?.close : (lastDaily ? lastDaily.open : bar.open);
  const pct = prev ? ((bar.close - prev) / prev) * 100 : null;
  const intraday = q && bar.time;
  return (
    <div className="qbar">
      <span className="ql code">{code}</span>
      <span className="ql px">{n2(bar.close)}</span>
      {pct != null && <span className={'ql ' + (pct >= 0 ? 'up' : 'dn')}>{pct >= 0 ? '+' : ''}{pct.toFixed(2)}%</span>}
      <span className="ql muted">H {n2(bar.high)} · L {n2(bar.low)}</span>
      <span className="ql muted">量 {bar.volume != null ? Number(bar.volume).toLocaleString() : '—'}</span>
      <span className="ql muted">{intraday ? '5m' : '日K'}</span>
      <FollowStrip code={code} latest={latestRow} latestBar={bar} />
    </div>
  );
}
