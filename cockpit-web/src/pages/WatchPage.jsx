import { useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { HELPER } from '../lib/data.js';

// D7/W5 — NVIDIA `/watch` 觀察 (docs/NVIDIA_WATCH_PAGE.md + NVIDIA Portfolio Tracker layout).
// Self-built React, NOT a Streamlit iframe.
// Data: data/watch/nvidia/holdings.json + timeline.json (static 13F/strategic facts, via :8778→:8790)
//       + live quotes (:8790 /watch/nvidia, Finnhub if key else seed)
//       + enrich: YTD / P-E(TTM) / MktCap / 52W high / news (Finnhub, 10-min cache on the Mac).
// US tickers get live data; NAVER/FANUC (KR/JP) fall back to seed_price. Never shows keys.
// tw_code → /symbol/:tw_code; US-only → details drawer.

const GROUPS = [
  { key: 'new', title: '2026 New Investments', tag: 'NEW', tone: 'up' },
  { key: 'current', title: 'Current Holdings · Q1 2026 13F', tag: 'CORE', tone: 'accent' },
  { key: 'partnership', title: 'Strategic Partnership', tag: 'PARTNER', tone: 'accent' },
  { key: 'exited', title: 'Exited（觀察）', tag: 'EXITED', tone: 'dn' },
];
const TABS = ['Portfolio', 'Performance', 'Sectors', 'News', '13F History'];

const usd = (n) => (n >= 1e12 ? '$' + (n / 1e12).toFixed(2) + 'T' : n >= 1e9 ? '$' + (n / 1e9).toFixed(n >= 1e10 ? 0 : 1) + 'B' : n >= 1e6 ? '$' + (n / 1e6).toFixed(0) + 'M' : '$' + n);
const pct = (v) => (v == null ? '—' : (v >= 0 ? '+' : '') + v + '%');
const pctCls = (v) => (v == null ? 'muted' : v > 0 ? 'up' : v < 0 ? 'dn' : 'muted');

export default function WatchPage() {
  const [data, setData] = useState(null);
  const [err, setErr] = useState('');
  const [loadingEnrich, setLoadingEnrich] = useState(false);
  const [sort, setSort] = useState('investment');
  const [tab, setTab] = useState('Portfolio');
  const [newsFilter, setNewsFilter] = useState('all');
  const [drawer, setDrawer] = useState(null);
  const [thir, setThir] = useState(null);

  const load13f = () => {
    fetch(`${HELPER}/watch/thirteen_f`)
      .then(r => (r.ok ? r.json() : null))
      .then(d => { if (d && d.quarters) setThir(d); })
      .catch(() => {});
  };

  const load = (refresh) => {
    setLoadingEnrich(true);
    fetch(`${HELPER}/watch/nvidia${refresh ? '?refresh=1' : ''}`)
      .then(r => (r.ok ? r.json() : null))
      .then(d => {
        if (d && d.holdings) {
          setData(d); setErr('');
          // enrich (YTD/P-E/MktCap/news) is filled by a background thread on the Mac
          // (10-min cache). If this load predates it, poll again a few times.
          const e = d.enrich || {};
          if (!e.metrics || Object.keys(e.metrics).length === 0) {
            polls.current += 1;
            if (polls.current < 6) setTimeout(() => loadRef.current(false), 8000);
          }
        } else setErr('helper offline — 顯示空態');
        setLoadingEnrich(false);
      })
      .catch(() => { setErr('helper offline — 顯示空態'); setLoadingEnrich(false); });
  };
  const polls = useRef(0);
  const loadRef = useRef(null);
  loadRef.current = load;
  useEffect(() => {
    load(false);
    return () => { polls.current = 0; };
  }, []); // eslint-disable-line

  useEffect(() => {
    if (tab === '13F History' && !thir) load13f();
  }, [tab]); // eslint-disable-line

  const holdings = (data?.holdings?.holdings) || [];
  const timeline = (data?.timeline?.events) || [];
  const quotes = useMemo(() => {
    const m = {};
    for (const q of (data?.quotes) || []) m[q.ticker] = q;
    return m;
  }, [data]);
  const metrics = (data?.enrich?.metrics) || {};
  const newsBy = (data?.enrich?.news) || {};

  const sorted = (list) => {
    const q = (x) => quotes[x.ticker] || {};
    const m = (x) => metrics[x.ticker] || {};
    let r = list.slice();
    if (sort === 'investment') r.sort((a, b) => (b.investment_usd || 0) - (a.investment_usd || 0));
    else if (sort === 'ytd') r.sort((a, b) => (m(b.ticker)?.ytd_pct ?? -999) - (m(a.ticker)?.ytd_pct ?? -999));
    else if (sort === 'daily') r.sort((a, b) => ((q(b.ticker)?.change_pct) ?? -999) - ((q(a.ticker)?.change_pct) ?? -999));
    else r.sort((a, b) => (a.name || '').localeCompare(b.name || ''));
    return r;
  };

  // Summary strip（只對有數值的算，不硬湊）
  const sum = useMemo(() => {
    const tracked = holdings.filter(h => h.status !== 'exited');
    const ytds = tracked.map(h => metrics[h.ticker]?.ytd_pct).filter(v => v != null);
    const vs52 = tracked.map(h => {
      const q = quotes[h.ticker] || {}; const hi = metrics[h.ticker]?.high52;
      if (typeof q.price === 'number' && q.price > 0 && hi != null && hi > 0) return (q.price / hi - 1) * 100;
      return null;
    }).filter(v => v != null);
    const partners = tracked.filter(h => h.status === 'partnership').length;
    const exited = holdings.filter(h => h.status === 'exited').length;
    const invested = holdings.filter(h => h.investment_usd && h.group === 'new').reduce((s, h) => s + h.investment_usd, 0);
    const avg = (a) => a.length ? a.reduce((s, v) => s + v, 0) / a.length : null;
    return {
      n3f: tracked.length - partners, partners, exited,
      invested,
      avgYtd: avg(ytds), bestYtd: ytds.length ? Math.max(...ytds) : null, worstYtd: ytds.length ? Math.min(...ytds) : null,
      avgVs52: avg(vs52),
      newsN: Object.values(newsBy).reduce((s, arr) => s + (arr?.length || 0), 0),
    };
  }, [holdings, metrics, quotes, newsBy]);

  // Sectors aggregation（13F facts by investment_usd）
  const sectors = useMemo(() => {
    const m = {};
    for (const h of holdings.filter(x => x.status !== 'exited')) {
      const k = h.sector || '未分類';
      m[k] = m[k] || { name: k, n: 0, usd: 0 };
      m[k].n += 1; m[k].usd += (h.investment_usd || 0);
    }
    return Object.values(m).sort((a, b) => b.usd - a.usd);
  }, [holdings]);
  const maxUsd = Math.max(1, ...sectors.map(s => s.usd));

  // News list（all + per ticker）
  const news = useMemo(() => {
    const arr = [];
    for (const [t, items] of Object.entries(newsBy)) {
      for (const n of items || []) arr.push({ ticker: t, ...n });
    }
    arr.sort((a, b) => (b.time || 0) - (a.time || 0));
    return newsFilter === 'all' ? arr : arr.filter(n => n.ticker === newsFilter);
  }, [newsBy, newsFilter]);
  const newsTickers = Object.keys(newsBy).sort();

  const priceCell = (h) => {
    const q = quotes[h.ticker] || {};
    if (typeof q.price === 'number' && q.price > 0) return <span>{q.price}</span>;
    // finnhub returns c:0 for non-US (NAVER/FANUC) -> seed price (13F 手整值)
    return <span className="muted" title="非 Finnhub 美股報價 — seed">{h.seed_price || '—'}</span>;
  };

  const renderRows = (list, tag, tone) => list.map(h => {
    const q = quotes[h.ticker] || {};
    const m = metrics[h.ticker] || {};
    const tw = h.tw_code;
    return (
      <div key={h.ticker} className="wrow" onClick={() => setDrawer(h)}>
        <span className="wco">
          {tw
            ? <Link to={`/symbol/${tw}`} onClick={e => e.stopPropagation()}>{h.name} <em className="muted">↔ {tw}</em></Link>
            : <b>{h.name}</b>}
          <i className={'wstat ' + tone}>{tag}</i>
          <small className="muted">{h.ticker} · {(h.tags || []).join(' ')}</small>
        </span>
        {priceCell(h)}
        <span className={pctCls(q.change_pct)}>{q.change_pct != null ? pct(q.change_pct) : '—'}</span>
        <span className={pctCls(m.ytd_pct)}>{pct(m.ytd_pct)}</span>
        <span>{m.mkt_cap_b != null ? usd(m.mkt_cap_b * 1e9) : '—'}</span>
        <span className="muted">{m.pe_ttm != null ? m.pe_ttm + 'x' : '—'}</span>
        <span className="muted">›</span>
      </div>
    );
  });

  const head = (
    <div className="wrow whead">
      <span>Company</span><span>Price</span><span>Daily</span><span>YTD</span><span>Mkt Cap</span><span>P/E</span><span></span>
    </div>
  );

  const usd13 = (n) => (n >= 1e9 ? '$' + (n / 1e9).toFixed(n >= 1e10 ? 0 : 1) + 'B' : n >= 1e6 ? '$' + (n / 1e6).toFixed(0) + 'M' : '$' + n);
  const pkey = (p) => { const m = /^(\d{2})-(\d{2})-(\d{4})$/.exec(p || ''); return m ? (+m[3] * 10000 + +m[1] * 100 + +m[2]) : 0; };
  const qs = (thir && thir.quarters) ? thir.quarters.slice().sort((a, b) => pkey(a.period) - pkey(b.period)) : [];
  const curQ = qs.length ? qs[qs.length - 1] : null;
  const d = thir && thir.diffs && thir.diffs.length ? thir.diffs[thir.diffs.length - 1] : null;
  const dprev = thir && thir.diffs && thir.diffs.length > 1 ? thir.diffs[thir.diffs.length - 2] : null;

  return (
    <div className="page watch">
      <div className="watch-top">
        <div>
          <div className="hs">NVIDIA 觀察 · 美側生態窗</div>
          <div className="muted">本頁＝美 NVIDIA 生態觀察（13F／戰略），≠ 台股 /live · {holdings.length} 檔 · 季度手整</div>
        </div>
        <div className="watch-badges">
          <span className={'pill ' + (data?.quotes_source === 'finnhub' ? 'up' : 'muted')}>
            Quotes: {data?.quotes_source === 'finnhub' ? 'Finnhub' : 'seed'}
          </span>
          {loadingEnrich && <span className="pill">refreshing…</span>}
          {err && <span className="pill dn">{err}</span>}
          <button className="btn" onClick={() => load(true)}>↻ Refresh</button>
        </div>
      </div>

      {/* Summary strip（tracker top cards） */}
      <div className="wsummary">
        <div className="wsum"><span className="muted">13F Holdings</span><b>{sum.n3f} stocks</b><small>{sum.partners} partners · {sum.exited} exited</small></div>
        <div className="wsum"><span className="muted">Invested（2026 new）</span><b>{sum.invested ? usd(sum.invested) + '+' : '—'}</b><small>disclosed stakes</small></div>
        <div className="wsum"><span className="muted">Avg YTD（live）</span><b className={pctCls(sum.avgYtd)}>{sum.avgYtd != null ? pct(sum.avgYtd) : '—'}</b>
          <small>{sum.bestYtd != null ? 'best ' + pct(sum.bestYtd) + ' · worst ' + pct(sum.worstYtd) : '—'}</small></div>
        <div className="wsum"><span className="muted">vs 52W High</span><b className={pctCls(sum.avgVs52)}>{sum.avgVs52 != null ? pct(sum.avgVs52) : '—'}</b><small>median approx</small></div>
      </div>

      <div className="watch-layout">
        <aside className="watch-side">
          <div className="wcard">
            <h4>Sort</h4>
            <select className="wselect" value={sort} onChange={e => setSort(e.target.value)}>
              <option value="investment">Investment</option>
              <option value="ytd">YTD</option>
              <option value="daily">Daily</option>
              <option value="name">Name</option>
            </select>
          </div>
          <div className="wcard">
            <h4>Recent Investments</h4>
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
              {GROUPS.map(g => {
                const gkey = (h) => h.group || (h.status === 'exited' ? 'exited' : h.status === 'partnership' ? 'partnership' : 'current');
                const list = sorted(holdings.filter(h => gkey(h) === g.key));
                if (!list.length) return null;
                return (
                  <div key={g.key} className="wgroup">
                    <div className="wgroup-head">{g.title}</div>
                    {head}
                    {renderRows(list, g.tag, g.tone)}
                  </div>
                );
              })}
            </div>
          )}

          {tab === 'Performance' && (
            <div className="wperf">
              <p className="muted">YTD（Finnhub yearToDatePriceReturnDaily）；無 live 時以投資量級代替</p>
              <div className="wperf-bars">
                {holdings.filter(h => h.status !== 'exited').slice(0, 12).map(h => {
                  const m = metrics[h.ticker] || {};
                  const hasLive = m.ytd_pct != null;
                  const v = hasLive ? Math.abs(m.ytd_pct) : Math.log10((h.investment_usd || 1) / 1e6 + 1);
                  return (
                    <div key={h.ticker} className="wperf-row">
                      <span className="muted">{h.name}</span>
                      <div className="wperf-track"><div className={'wperf-fill ' + (hasLive && m.ytd_pct < 0 ? 'dn' : 'up')} style={{ width: Math.min(100, v * 4 + 6) + '%' }} /></div>
                      <span className={hasLive ? pctCls(m.ytd_pct) : 'muted'}>{hasLive ? pct(m.ytd_pct) : (h.investment_usd ? usd(h.investment_usd) : '—')}</span>
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
                  <div className="wsector-head"><span>{s.name}</span><span className="muted">{s.n} 檔 · {s.usd ? usd(s.usd) : '—'}</span></div>
                  <div className="wperf-track"><div className="wperf-fill up" style={{ width: (s.usd / maxUsd * 100) + '%' }} /></div>
                </div>
              ))}
            </div>
          )}

          {tab === 'News' && (
            <div className="wnews">
              <div className="wnews-bar">
                <button className={'wnews-chip' + (newsFilter === 'all' ? ' on' : '')} onClick={() => setNewsFilter('all')}>All（{sum.newsN}）</button>
                {newsTickers.map(t => (
                  <button key={t} className={'wnews-chip' + (newsFilter === t ? ' on' : '')} onClick={() => setNewsFilter(t)}>{t}</button>
                ))}
              </div>
              {news.length === 0 && <div className="muted">無新聞（Finnhub 30d）或尚未載入 — 點右上角 ↻ Refresh。</div>}
              <div className="wnews-list">
                {news.map((n, i) => (
                  <div key={i} className="wnews-item">
                    <span className="wnews-tick">{n.ticker}</span>
                    <span className="wnews-hd">
                      {n.url
                        ? <a href={n.url} target="_blank" rel="noopener noreferrer" onClick={e => e.stopPropagation()}>{n.headline}</a>
                        : n.headline}
                    </span>
                    <span className="muted wnews-meta">{n.source}{n.time ? ' · ' + new Date(n.time * 1000).toLocaleDateString('en-CA') : ''}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {tab === '13F History' && (
            <div className="w13f">
              {!thir && <div className="muted">載入中…（:8790 /watch/thirteen_f）</div>}
              {thir && thir.quarters.length === 0 && <div className="muted">無 13F 季度資料（data/watch/nvidia/thirteen_f/*.json 未 seed）</div>}
              {d && (
                <div className="w13f-block">
                  <div className="w13f-head">
                    <b>季度 Diff：{d.from_period} → {d.to_period}</b>
                    <span className="muted">（{d.from} → {d.to} · 來源：{thir.source}）</span>
                  </div>
                  <div className="w13f-diff">
                    {d.added.length === 0 && d.removed.length === 0 && d.changed.length === 0
                      ? <div className="muted">本季無變動</div>
                      : null}
                    {d.added.map(h => (
                      <div key={'a' + h.cusip} className="w13f-row up">
                        <span>＋ 新增</span><span>{h.name}</span>
                        <span>{h.class}</span><span>{usd13(h.value_usd)}</span>
                      </div>
                    ))}
                    {d.removed.map(h => (
                      <div key={'r' + h.cusip} className="w13f-row dn">
                        <span>－ 退出</span><span>{h.name}</span>
                        <span>{h.class}</span><span>{usd13(h.value_usd)}（上季）</span>
                      </div>
                    ))}
                    {d.changed.map(h => (
                      <div key={'c' + h.cusip} className="w13f-row">
                        <span>〜 調整</span><span>{h.name}</span>
                        <span>{usd13(h.from_usd)} → {usd13(h.to_usd)}</span>
                        <span className={h.pct >= 0 ? 'up' : 'dn'}>{h.pct >= 0 ? '+' : ''}{h.pct}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {thir && curQ && (
                <div className="w13f-block">
                  <div className="w13f-head">
                    <b>最新持倉：{curQ.period}</b>
                    <span className="muted">{curQ.holdings.length} 檔 · 合計 {usd13(curQ.total_usd)} · SEC accession {curQ.accession}</span>
                  </div>
                  <div className="wtable">
                    <div className="wrow whead">
                      <span>Issuer</span><span>Class</span><span>Shares</span><span>Value</span><span>% 組合</span><span></span>
                    </div>
                    {curQ.holdings.map(h => (
                      <div key={h.cusip} className="wrow">
                        <span className="wco"><b>{h.name}</b><small className="muted">{h.cusip}</small></span>
                        <span className="muted">{h.class}</span>
                        <span>{(h.shares || '0').replace(/\B(?=(\d{3})+(?!\d))/g, ',')}</span>
                        <span>{usd13(h.value_usd)}</span>
                        <span className="muted">{((h.value_usd / curQ.total_usd) * 100).toFixed(1)}%</span>
                        <span className="muted">›</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              {qs.length > 1 && (
                <div className="w13f-block">
                  <div className="w13f-head"><b>各季總覽</b></div>
                  <div className="w13f-qs">
                    {qs.map(q => (
                      <div key={q.period} className="w13f-q">
                        <span className="muted">{q.period}</span>
                        <b>{usd13(q.total_usd)}</b>
                        <small>{q.holdings.length} 檔</small>
                      </div>
                    ))}
                  </div>
                </div>
              )}
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
            {drawer.investment_usd && <p className="muted">Stake: {usd(drawer.investment_usd)}</p>}
            {drawer.tw_code && <Link className="pill" to={`/symbol/${drawer.tw_code}`}>台股對照 → /symbol/{drawer.tw_code}</Link>}
            <button className="muted" style={{ marginTop: 8 }} onClick={() => setDrawer(null)}>關閉</button>
          </div>
        </div>
      )}
    </div>
  );
}
