import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { HELPER } from '../lib/data.js';

// D7 — NVIDIA `/watch` 觀察 (docs/NVIDIA_WATCH_PAGE.md). Self-built React, NOT a
// Streamlit iframe. Data: data/watch/nvidia/holdings.json + timeline.json (static,
// served by :8778) + live quotes via :8790 /watch/nvidia (Finnhub if key else seed).
// tw_code → /symbol/:tw_code; US-only → details drawer. Never shows keys.

const STATUS_LABEL = { current: '持倉 13F', partnership: '戰略夥伴', exited: '已退出' };
const STATUS_TONE = { current: 'up', partnership: 'accent', exited: 'dn' };
const STATUS_ORDER = { current: 0, partnership: 1, exited: 2 };
const TABS = ['Portfolio', 'Performance', 'Sectors', 'News', '13F History'];

export default function WatchPage() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState('');
  const [statuses, setStatuses] = useState(['current', 'partnership', 'exited']);
  const [sort, setSort] = useState('investment');
  const [tab, setTab] = useState('Portfolio');
  const [drawer, setDrawer] = useState(null);

  useEffect(() => {
    const t = setTimeout(() => {
      fetch(`${HELPER}/watch/nvidia`).then(r => (r.ok ? r.json() : null)).then(d => {
        if (d && d.holdings) setData(d); else setErr('helper offline — 顯示空態');
      }).catch(() => setErr('helper offline — 顯示空態'));
    }, 0);
    return () => clearTimeout(t);
  }, []);

  const holdings = (data?.holdings?.holdings) || [];
  const timeline = (data?.timeline?.events) || [];
  const quotes = useMemo(() => {
    const m = {};
    for (const q of (data?.quotes) || []) m[q.ticker] = q;
    return m;
  }, [data]);

  const rows = useMemo(() => {
    let r = holdings.filter(h => statuses.includes(h.status));
    const q = (x) => quotes[x.ticker] || {};
    if (sort === 'investment') r = r.slice().sort((a, b) => (b.investment_usd || 0) - (a.investment_usd || 0));
    else if (sort === 'ytd') r = r.slice().sort((a, b) => ((q(b.ticker)?.change_pct) ?? -999) - ((q(a.ticker)?.change_pct) ?? -999));
    else if (sort === 'daily') r = r.slice().sort((a, b) => ((q(b.ticker)?.change_pct) ?? -999) - ((q(a.ticker)?.change_pct) ?? -999));
    else r = r.slice().sort((a, b) => (a.name || '').localeCompare(b.name || ''));
    return r;
  }, [holdings, statuses, sort, quotes]);

  const qsrc = data?.quotes_source;
  const qOpen = (data?.quotes || []).some(q => q.market === 'open');

  // Sectors aggregation (by holdings.sector, investment weight)
  const sectors = useMemo(() => {
    const m = {};
    for (const h of holdings.filter(x => statuses.includes(x.status))) {
      const k = h.sector || '未分類';
      m[k] = m[k] || { name: k, n: 0, usd: 0 };
      m[k].n += 1; m[k].usd += (h.investment_usd || 0);
    }
    return Object.values(m).sort((a, b) => b.usd - a.usd);
  }, [holdings, statuses]);
  const maxUsd = Math.max(1, ...sectors.map(s => s.usd));

  return (
    <div className="page watch">
      <div className="watch-top">
        <div>
          <div className="hs">NVIDIA 觀察 · 美側生態窗</div>
          <div className="muted">本頁＝美 NVIDIA 生態觀察（13F／戰略），≠ 台股 /live · {holdings.length} 檔 · 季度手整</div>
        </div>
        <div className="watch-badges">
          <span className={'pill ' + (qsrc === 'finnhub' ? 'up' : 'muted')}>
            Quotes: {qsrc === 'finnhub' ? 'Finnhub' : 'seed'} {qsrc === 'finnhub' ? (qOpen ? '· OPEN' : '· CLOSED') : ''}
          </span>
          {err && <span className="pill dn">{err}</span>}
        </div>
      </div>

      <div className="watch-layout">
        <aside className="watch-side">
          <div className="wcard">
            <h4>狀態 Filter</h4>
            <div className="wfilters">
              {Object.entries(STATUS_LABEL).map(([k, lab]) => (
                <label key={k} className={'wchip ' + STATUS_TONE[k] + (statuses.includes(k) ? ' on' : '')}>
                  <input type="checkbox" checked={statuses.includes(k)}
                    onChange={e => setStatuses(s => e.target.checked ? [...s, k] : s.filter(x => x !== k))} />
                  {lab}
                </label>
              ))}
            </div>
            <h4>Sort</h4>
            <select className="wselect" value={sort} onChange={e => setSort(e.target.value)}>
              <option value="investment">Investment</option>
              <option value="ytd">YTD</option>
              <option value="daily">Daily</option>
              <option value="name">Name</option>
            </select>
          </div>
          <div className="wcard">
            <h4>Tag 圖例</h4>
            <div className="mtags muted">
              <span title="AI 晶片核心">core</span><span title="晶圓／封裝／材料">supply-chain</span>
              <span title="自訂晶片">custom-asic</span><span title="資料中心">data-center</span>
              <span title="戰略性持股">strategic</span><span title="合作">partnership</span>
            </div>
          </div>
          <div className="wcard">
            <h4>投資時間軸</h4>
            <div className="wtimeline">
              {timeline.length === 0 && <div className="muted">（seed 未填）</div>}
              {timeline.map((e, i) => (
                <div key={i} className="wtevent">
                  <span className="wte-date muted">{e.date}</span>
                  <span className="wte-tick">{e.ticker}</span>
                  <span className="wte-text">{e.text}</span>
                </div>
              ))}
            </div>
          </div>
        </aside>

        <section className="watch-main">
          <div className="wtabs">
            {TABS.map(t => <button key={t} className={'wtab' + (tab === t ? ' on' : '')} onClick={() => setTab(t)}>{t}</button>)}
          </div>

          {tab === 'Portfolio' && (
            <div className="wtable">
              <div className="wrow whead">
                <span>Company</span><span>Price</span><span>Daily%</span><span>Investment</span><span>Sector</span><span>Details</span>
              </div>
              {rows.length === 0 && <div className="muted" style={{ padding: 12 }}>（無符合 filter 的標的）</div>}
              {rows.map(h => {
                const q = quotes[h.ticker] || {};
                const tw = h.tw_code;
                return (
                  <div key={h.ticker} className="wrow" onClick={() => setDrawer(h)}>
                    <span className="wco">
                      {tw
                        ? <Link to={`/symbol/${tw}`} onClick={e => e.stopPropagation()}>{h.name} <em className="muted">↔ {tw}</em></Link>
                        : <b>{h.name}</b>}
                      <small className="muted">{h.ticker} · {(h.tags || []).join(' ')}</small>
                      <i className={'wstat ' + STATUS_TONE[h.status]}>{STATUS_LABEL[h.status] || h.status}</i>
                    </span>
                    <span>{q.price != null ? q.price : '—'}</span>
                    <span className={q.change_pct > 0 ? 'up' : q.change_pct < 0 ? 'dn' : ''}>{q.change_pct != null ? (q.change_pct >= 0 ? '+' : '') + q.change_pct + '%' : '—'}</span>
                    <span>{h.investment_usd ? '$' + (h.investment_usd / 1e9).toFixed(h.investment_usd >= 1e9 ? 0 : 1) + 'B' : '—'}</span>
                    <span className="muted">{h.sector || '—'}</span>
                    <span className="muted">›</span>
                  </div>
                );
              })}
            </div>
          )}

          {tab === 'Performance' && (
            <div className="wperf">
              <p className="muted">YTD 多線比價（seed 模式：無報價時顯示投資量級；有 Finnhub 報價後改以 % 變化繪製）</p>
              <div className="wperf-bars">
                {rows.slice(0, 10).map(h => {
                  const q = quotes[h.ticker] || {};
                  const v = q.change_pct != null ? Math.abs(q.change_pct) : Math.log10((h.investment_usd || 1) / 1e6 + 1);
                  return (
                    <div key={h.ticker} className="wperf-row">
                      <span className="muted">{h.name}</span>
                      <div className="wperf-track"><div className={'wperf-fill ' + (q.change_pct != null && q.change_pct < 0 ? 'dn' : 'up')} style={{ width: Math.min(100, v * 6) + '%' }} /></div>
                      <span className={q.change_pct > 0 ? 'up' : q.change_pct < 0 ? 'dn' : 'muted'}>{q.change_pct != null ? (q.change_pct >= 0 ? '+' : '') + q.change_pct + '%' : (h.investment_usd ? '$' + (h.investment_usd / 1e9).toFixed(1) + 'B' : '—')}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {tab === 'Sectors' && (
            <div className="wsectors">
              {sectors.map(s => (
                <div key={s.name} className="wsector">
                  <div className="wsector-head"><span>{s.name}</span><span className="muted">{s.n} 檔 · {s.usd ? '$' + (s.usd / 1e9).toFixed(1) + 'B' : '—'}</span></div>
                  <div className="wperf-track"><div className="wperf-fill up" style={{ width: (s.usd / maxUsd * 100) + '%' }} /></div>
                </div>
              ))}
            </div>
          )}

          {tab === 'News' && (
            <div className="wnews muted">
              新聞端點待接（:8790 /watch/news，需 Finnhub/FinMind 美股 key）。
              目前以 Timeline 事件代替；無 key 時維持空態＋說明，不顯示金鑰。
            </div>
          )}

          {tab === '13F History' && (
            <div className="w13f muted">
              季度 13F 表（data/watch/nvidia/thirteen_f/*.json）尚未 seed — 手整一版後於此呈現季度持倉 diff。
            </div>
          )}
        </section>
      </div>

      {drawer && (
        <div className="wdrawer" onClick={() => setDrawer(null)}>
          <div className="wdrawer-inner" onClick={e => e.stopPropagation()}>
            <h3>{drawer.name} <span className="muted">{drawer.ticker}</span></h3>
            <div className="muted">{(drawer.tags || []).join(' · ') || '—'} · {drawer.sector || '—'}</div>
            <p>{drawer.note || '（無筆記）'}</p>
            {drawer.tw_code && <Link className="pill" to={`/symbol/${drawer.tw_code}`}>台股對照 → /symbol/{drawer.tw_code}</Link>}
            <button className="muted" style={{ marginTop: 8 }} onClick={() => setDrawer(null)}>關閉</button>
          </div>
        </div>
      )}
    </div>
  );
}
