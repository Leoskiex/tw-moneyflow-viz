import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { getFundFlo, jget, DATA, n2, recapRows } from '../lib/data.js';
import { listRecent } from '../lib/symbolStore.js';
import StoryChapters from '../features/story/StoryChapters.jsx';
import FundRank from '../features/story/FundRank.jsx';
import CmiBadge from '../features/cmi/CmiBadge.jsx';
import ActionRadar from '../features/radar/ActionRadar.jsx';
import DigestPanel from '../features/story/DigestPanel.jsx';
import HeatTw from '../features/heat/HeatTw.jsx';

// / — 今日 (D1: FundFlo 五章故事 + 水流排行 遷入 SPA，讀同一 data/fundflo JSON)
// 名稱／代號點擊 → /symbol/:code（keep code）。舊 :8777/fund-flow.html 不再是唯一入口。
export default function Home() {
  const [ff, setFF] = useState(null);
  const [regime, setRegime] = useState(null);
  const [live, setLive] = useState(null);
  const [recap, setRecap] = useState(null);
  const [recent, setRecent] = useState(listRecent());
  const [q, setQ] = useState('');

  useEffect(() => {
    (async () => {
      setFF(await getFundFlo());
      setRegime(await jget(DATA('data/regime_latest.json')));
      setLive(await jget(DATA('data/live/latest.json')));
      setRecap(await recapRows());
    })();
  }, []);

  const nStocks = (ff?.stocks || []).length;
  const OUTC = { hit_target: ['到目標', 'up'], hit_stop: ['到止損', 'dn'], held_range: ['守住區間', 'up'], broke_range: ['破區間', 'dn'], open: ['進行中', ''] };

  return (
    <div className="page home">
      <div className="topstrip">
        <div>
          <div className="hs">今日 · 錢怎麼走</div>
          <div className="muted">
            {ff?.meta?.date || '—'}
            {regime?.primary_label ? ` · 市況 ${regime.primary_label}` : ''}
            {nStocks ? ` · ${nStocks} 檔水流` : ''}
          </div>
        </div>
        <div className="strip-right">
          <CmiBadge />
          {live && <Link to="/live" className="pill" style={{ color: 'var(--accent)' }}>盤中：{live.events?.length ?? 0} 條</Link>}
        </div>
      </div>

      <div className="quickbar">
        <input className="qb-input" placeholder="代碼直達，如 2454" value={q}
          onChange={e => setQ(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && q.trim()) { location.href = `./symbol/${q.trim().toUpperCase()}`; setQ(''); } }} />
        {recent.slice(0, 6).map(c => <Link key={c} className="chip" to={`/symbol/${c}`}>{c}</Link>)}
        {(ff?.stocks || []).slice(0, 8).map(s => <Link key={s.code} className="chip" to={`/symbol/${s.code}`}>{s.code} {s.name}</Link>)}
        <span className="qb-links muted">
          <Link to="/flow">盤面 泡泡</Link>
          <Link to="/heat">熱力</Link>
          <Link to="/board">看圖版</Link>
          <a href="http://127.0.0.1:8765/" target="_blank" rel="noreferrer" className="qb-ext">產業地圖 ↗</a>
        </span>
      </div>

      <div className="home-grid">
        <div className="home-main">
          <StoryChapters />
          <FundRank />
          <div style={{ marginBottom: 10 }}>
            <div className="secbar">
              <h3 style={{ display: 'inline' }}>熱力</h3>
              <Link to="/heat" className="muted" style={{ fontSize: 12 }}>完整熱力 →</Link>
            </div>
            <HeatTw compact />
          </div>
          <DigestPanel />
          <ActionRadar />

          {recap && recap.length > 0 && (
            <>
              <h3>盤後復盤（上次凍結 → 現價結果）</h3>
              <div className="board recap">
                {recap.map((r) => {
                  const o = r.outcome || {};
                  const [lbl, tone] = OUTC[o.status] || OUTC.open;
                  return (
                    <Link key={r.code} className="brow" to={`/symbol/${r.code}`}>
                      <span className="bc">{r.code}</span>
                      <span className="bn muted">{o.direction === 'long' ? '多' : o.direction === 'short' ? '空' : '觀望'}</span>
                      <span className="bpct">{o.anchor != null ? n2(o.anchor) : ''}{o.last != null ? ` → ${n2(o.last)}` : ''}</span>
                      <span className={'bpct ' + (o.pct == null ? '' : o.pct >= 0 ? 'up' : 'dn')}>{o.pct != null ? (o.pct >= 0 ? '+' : '') + o.pct + '%' : '—'}</span>
                      <span className={'bpct ' + tone}>{lbl}</span>
                    </Link>
                  );
                })}
              </div>
            </>
          )}
        </div>

        <aside className="home-side">
          <div className="card">
            <h3>盤中 Live（:8790 hunter）</h3>
            <div className="kv">
              {(!live || !live.events || !live.events.length) && <div className="muted">尚無事件（TW 09:00–13:30 session 內由 :8790 livescan 產生）</div>}
              {(live?.events || []).slice(0, 8).map((e, i) => (
                <Link key={i} className="evrow" to={`/symbol/${e.code}`}>
                  <span className="ek">{e.kind}</span>
                  <span className="ec">{e.code} {e.name}</span>
                  <span className="ed muted">{e.detail}</span>
                </Link>
              ))}
              {live?.events?.length > 0 && <Link to="/live" className="muted" style={{ fontSize: 12 }}>全部 {live.events.length} 條 →</Link>}
            </div>
          </div>
          <div className="card">
            <h3>導航</h3>
            <div className="kv">
              <Link to="/flow" style={{ display: 'block', padding: '3px 0' }}>盤面 泡泡圖 →</Link>
              <Link to="/heat" style={{ display: 'block', padding: '3px 0' }}>台股熱力 →</Link>
              <Link to="/board" style={{ display: 'block', padding: '3px 0' }}>看圖版 →</Link>
              <Link to="/watch" style={{ display: 'block', padding: '3px 0' }}>NVIDIA 觀察 →</Link>
              <Link to="/live" style={{ display: 'block', padding: '3px 0' }}>盤中 Live →</Link>
              <Link to="/symbol" style={{ display: 'block', padding: '3px 0' }}>個股搜尋 →</Link>
              <Link to="/sepa" style={{ display: 'block', padding: '3px 0' }}>SEPA 模板 →</Link>
              <Link to="/research" style={{ display: 'block', padding: '3px 0' }}>研究庫 →</Link>
              <Link to="/settings" style={{ display: 'block', padding: '3px 0' }}>設置 →</Link>
              <div className="muted" style={{ marginTop: 6 }}>舊頁 :8777 入口已導向本站</div>
            </div>
          </div>
        </aside>
      </div>
    </div>
  );
}
