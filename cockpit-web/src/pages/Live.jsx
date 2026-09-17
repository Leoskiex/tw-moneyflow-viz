import { useEffect, useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { jget, DATA, n2 } from '../lib/data.js';

// /live — INTRADAY_LIVE_WATCH stream (data/live/latest.json via :8790 hunter).
// Event ts from hunter is Unix **seconds** (bar time or scan time).
const TZ = 'Asia/Taipei';
const KIND_ZH = {
  vol_spike: '爆量',
  rs_burst: '相對強勢',
  break: '均線',
  ma_break: '均線',
  frozen: '凍結位',
  freeze: '凍結位',
  sector: '題材連動',
  sector_heat: '題材連動',
};

function tsMs(ts) {
  if (ts == null || ts === '') return null;
  const n = Number(ts);
  if (!Number.isFinite(n)) return null;
  // seconds vs ms
  return n < 1e12 ? n * 1000 : n;
}

function fmtWhen(ts) {
  const ms = tsMs(ts);
  if (ms == null) return '';
  const d = new Date(ms);
  const clock = d.toLocaleTimeString('zh-TW', { timeZone: TZ, hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
  const day = d.toLocaleDateString('zh-TW', { timeZone: TZ, month: '2-digit', day: '2-digit' });
  const ageMin = Math.max(0, Math.round((Date.now() - ms) / 60000));
  const age = ageMin < 1 ? '剛剛' : ageMin < 60 ? `${ageMin} 分前` : `${Math.round(ageMin / 60)} 小時前`;
  return `${day} ${clock}（${age}）`;
}

function todayKeyTPE() {
  return new Date().toLocaleDateString('en-CA', { timeZone: TZ }); // YYYY-MM-DD
}

function dayKeyTPE(ts) {
  const ms = tsMs(ts);
  if (ms == null) return '';
  return new Date(ms).toLocaleDateString('en-CA', { timeZone: TZ });
}

export default function Live() {
  const [latest, setLatest] = useState(null);
  const [watchlist, setWatchlist] = useState(null);
  const [err, setErr] = useState('');
  const [quiet, setQuiet] = useState(false);
  const [todayOnly, setTodayOnly] = useState(true);
  const [now, setNow] = useState(Date.now());

  useEffect(() => {
    let dead = false;
    const pull = async () => {
      const l = await jget(DATA('data/live/latest.json'));
      if (!dead) {
        setLatest(l);
        setErr(l ? '' : 'data/live/latest.json 不存在（hunter 尚未跑過 / session 外）');
        setNow(Date.now());
      }
      const w = await jget(DATA('data/live/watchlist.json'));
      if (!dead) setWatchlist(w);
    };
    pull();
    const id = setInterval(pull, 15000);
    return () => { dead = true; clearInterval(id); };
  }, []);

  const today = todayKeyTPE();
  const events = useMemo(() => {
    const raw = (latest?.events || []).slice().reverse();
    return raw.filter((e) => {
      if (todayOnly && dayKeyTPE(e.ts) !== today) return false;
      if (quiet && !(e.sector || e.kind === 'frozen' || e.kind === 'freeze')) return false;
      return true;
    });
  }, [latest, quiet, todayOnly, today]);

  const allEvents = latest?.events || [];
  const session = latest?.session;
  const kinds = {};
  events.forEach((e) => { kinds[e.kind] = (kinds[e.kind] || 0) + 1; });
  const genMs = tsMs(latest?.generated_at);
  const genAge = genMs != null ? Math.max(0, Math.round((now - genMs) / 1000)) : null;

  return (
    <div className="page live">
      <div className="topstrip">
        <div>
          <div className="hs">盤中 Live · 5m hunter</div>
          <div className="muted">
            {session ? `session：${session.label}（${session.range}）` : 'session 狀態未知'}
            {' · '}時區 Asia/Taipei
            {genAge != null && ` · 資料 ${genAge < 60 ? `${genAge}s 前更新` : `${Math.round(genAge / 60)} 分前更新`}`}
          </div>
        </div>
        <div className="strip-right">
          <label className="muted" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <input type="checkbox" checked={todayOnly} onChange={(e) => setTodayOnly(e.target.checked)} /> 只看今天
          </label>
          <label className="muted" style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <input type="checkbox" checked={quiet} onChange={(e) => setQuiet(e.target.checked)} /> quiet（僅產業卡+凍結）
          </label>
          <span className="pill">{events.length} 條今日 / 全庫 {allEvents.length}</span>
        </div>
      </div>

      <div className="kv" style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 12 }}>
        {Object.entries(kinds).map(([k, n]) => (
          <span key={k} className="pill">{KIND_ZH[k] || k} × {n}</span>
        ))}
        <span className="pill" style={{ color: 'var(--warn)' }}>分點 who-buys：[blocked: 需付費 feed]</span>
      </div>

      {watchlist && (
        <div className="card" style={{ marginBottom: 12 }}>
          <h3>Watchlist（{watchlist.length} 檔，cap 60）</h3>
          <div style={{ padding: 10, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {watchlist.map((c) => <Link key={c} className="chip" to={`/symbol/${c}`}>{c}</Link>)}
          </div>
        </div>
      )}

      {err && <div className="err">{err}</div>}

      <div className="stream">
        {events.length === 0 && !err && (
          <div className="muted" style={{ padding: 16 }}>
            {todayOnly ? '今天尚無事件（可取消「只看今天」看歷史）。' : '尚無事件。'}
          </div>
        )}
        {events.map((e, i) => (
          <div key={`${e.ts}-${e.code}-${e.kind}-${i}`} className={'evcard ' + (e.sector ? 'sector' : '')}>
            <div className="evhead">
              <span className="pill" style={{ color: e.sector ? 'var(--accent)' : 'var(--warn)' }}>
                {e.sector ? '產業卡' : (KIND_ZH[e.kind] || e.kind)}
              </span>
              <Link className="evcode" to={e.code ? `/symbol/${e.code}` : '/live'}>
                {e.sector ? (e.industry || '題材') : `${e.code} ${e.name || ''}`}
              </Link>
              <span className="muted">{fmtWhen(e.ts)}</span>
            </div>
            <div className="evdetail">{e.detail}</div>
            {e.refs && <div className="evrefs muted">ref: {e.refs.join('、')}</div>}
            {e.px != null && <div className="evpx muted">@ {n2(e.px)}</div>}
            {!e.sector && (
              <div className="evfund muted">
                T−1 法人（FundFlo）：{e.fundflo && e.fundflo.name
                  ? `${e.fundflo.name} 外資 ${n2(e.fundflo.foreign_flow_yi)} 億`
                  : '未收錄'}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
