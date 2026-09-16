import { useEffect, useState } from 'react';
import { followGet, followSet, followCancel, n2 } from '../../lib/data.js';

// #13 跟單 (kansoku FollowAction port, adapted to our data):
// toggle on → entry/target/stop prefilled from the latest frozen scenarios;
// persists to :8790 /follow; helper checks 5m close each /follow GET and flags
// target/stop touch. Banner shows the live trigger.
export default function FollowStrip({ code, latest, latestBar }) {
  const [st, setSt] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let live = true;
    const load = async () => { const s = await followGet(code); if (live) setSt(s); };
    load();
    const t = setInterval(load, 30000);
    return () => { live = false; clearInterval(t); };
  }, [code]);

  const on = st && st.following;
  const dir = on ? st.direction : (latest ? (latest.weights_pct?.bull >= latest.weights_pct?.bear ? 'long' : 'short') : 'long');
  const scn = latest?.scenarios || {};
  const entry0 = on ? st.entry : (dir === 'long' ? scn.base : scn.bear);
  const target0 = on ? st.target : (dir === 'long' ? scn.bull : scn.base);
  const stop0 = on ? st.stop : (dir === 'long' ? scn.bear : scn.base);

  const toggle = async () => {
    setBusy(true);
    if (on) { await followCancel(code); setSt({ following: false, code }); }
    else { const r = await followSet(code, entry0, target0, stop0); setSt(r.state || r); }
    setBusy(false);
  };

  return (
    <span className="follow-control">
      <span className="follow-label">跟單</span>
      <button className={'follow-sw' + (on ? ' on' : '')} onClick={toggle} disabled={busy}
        title={on ? `追蹤中：入 ${n2(st.entry)} → 目標 ${n2(st.target)} / 止損 ${n2(st.stop)}` : '按凍結檔預填 入場/目標/止損'}>
        {on ? '開' : '關'}
      </button>
      {on && (
        <>
          <span className="follow-nums muted">入 {n2(st.entry)} · 目標 {n2(st.target)} · 止損 {n2(st.stop)}</span>
          {st.trigger && (
            <span className={'follow-trig ' + (st.trigger === 'target' ? 'up' : 'dn')}>
              {st.trigger === 'target' ? '觸及目標' : '觸及止損'} {st.last != null ? n2(st.last) : ''}
            </span>
          )}
          {!st.trigger && st.last != null && <span className="follow-last muted">現 {n2(st.last)}</span>}
        </>
      )}
    </span>
  );
}
