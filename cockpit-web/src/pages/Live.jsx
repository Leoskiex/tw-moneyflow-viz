import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { jget, DATA, n2 } from '../lib/data.js';

// /live — INTRADAY_LIVE_WATCH: event stream from etl/live_watch.py (data/live/*.json).
// 分點 who-buys is explicitly labeled unavailable (no free feed).
export default function Live() {
  const [latest, setLatest] = useState(null);
  const [watchlist, setWatchlist] = useState(null);
  const [err, setErr] = useState('');
  const [quiet, setQuiet] = useState(false);

  useEffect(() => {
    let dead = false;
    const pull = async () => {
      const l = await jget(DATA('data/live/latest.json'));
      if (!dead) { setLatest(l); setErr(l ? '' : 'data/live/latest.json 不存在（etl/live_watch.py 尚未跑過 / session 外 quiet）'); }
      const w = await jget(DATA('data/live/watchlist.json'));
      if (!dead) setWatchlist(w);
    };
    pull();
    const id = setInterval(pull, 15000);
    return () => { dead = true; clearInterval(id); };
  }, []);

  const events = (latest?.events || []).slice().reverse();
  const shown = quiet ? events.filter(e => e.sector || e.kind === 'frozen') : events;
  const session = latest?.session;
  const kinds = {};
  events.forEach(e => { kinds[e.kind] = (kinds[e.kind] || 0) + 1; });

  return (
    <div className="page live">
      <div className="topstrip">
        <div>
          <div className="hs">盤中 Live · 5m hunter</div>
          <div className="muted">
            {session ? `session：${session.label}（${session.range} TPE）` : 'session 狀態未知'}
            {' · '}資料：data/live/latest.json（launchd :8790 hunter）
          </div>
        </div>
        <div className="strip-right">
          <label className="muted" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <input type="checkbox" checked={quiet} onChange={e => setQuiet(e.target.checked)} /> quiet（僅產業卡+凍結觸發）
          </label>
          <span className="pill">{events.length} 條 / {Object.keys(kinds).length} 類</span>
        </div>
      </div>

      <div className="kv" style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
        {Object.entries(kinds).map(([k, n]) => <span key={k} className="pill">{k} × {n}</span>)}
        <span className="pill" style={{ color: 'var(--warn)' }}>分點 who-buys：[blocked: 需付費 feed]</span>
      </div>

      {watchlist && (
        <div className="card" style={{ marginBottom: 12 }}>
          <h3>Watchlist（{watchlist.length} 檔，cap 60）</h3>
          <div style={{ padding: 10, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {watchlist.map(c => <Link key={c} className="chip" to={`/symbol/${c}`}>{c}</Link>)}
          </div>
        </div>
      )}

      {err && <div className="err">{err}</div>}

      <div className="stream">
        {shown.length === 0 && !err && <div className="muted" style={{ padding: 16 }}>尚無事件。</div>}
        {shown.map((e, i) => (
          <div key={i} className={'evcard ' + (e.sector ? 'sector' : '')}>
            <div className="evhead">
              <span className="pill" style={{ color: e.sector ? 'var(--accent)' : 'var(--warn)' }}>{e.sector ? '產業卡' : e.kind}</span>
              <Link className="evcode" to={`/symbol/${e.code}`}>{e.sector ? e.industry : `${e.code} ${e.name || ''}`}</Link>
              <span className="muted">{e.ts ? new Date(e.ts).toLocaleTimeString('en-GB', { timeZone: 'Asia/Taipei' }) : ''}</span>
            </div>
            <div className="evdetail">{e.detail}</div>
            {e.refs && <div className="evrefs muted">ref: {e.refs.join('、')}</div>}
            {e.px != null && <div className="evpx muted">@ {n2(e.px)}</div>}
            {!e.sector && (
              <div className="evfund muted">T−1 法人（FundFlo）：{e.fundflo && e.fundflo.name ? `${e.fundflo.name} 外資 ${n2(e.fundflo.foreign_flow_yi)} 億` : '未收錄'}</div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
