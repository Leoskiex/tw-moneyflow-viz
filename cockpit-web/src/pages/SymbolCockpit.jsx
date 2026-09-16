import { useEffect, useState, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import ChartPanel from '../features/charts/ChartPanel.jsx';
import SidebarTabs from '../features/cockpit/SidebarTabs.jsx';
import {
  loadDoc, helperStatus, helperEnsure, helperAsk, helperP2, p2State,
  getFundFlo, getJsonl, getNews, getEtf, getRegime, fundRow, n2,
  followGet, followSet, followCancel,
} from '../lib/data.js';
import { viewState, pushRecent, listRecent } from '../lib/symbolStore.js';
import QuoteBar from '../features/quotes/QuoteBar.jsx';

const TFS = ['1D', '60m', '15m', '5m'];

export default function SymbolCockpit() {
  const { sym } = useParams();
  const navigate = useNavigate();
  const code = (sym || '').toUpperCase();
  const vs = viewState(code);

  const [doc, setDoc] = useState(null);
  const [err, setErr] = useState('');
  const [fetching, setFetching] = useState(false);
  const [name, setName] = useState('');
  const [rows, setRows] = useState([]);
  const [ff, setFF] = useState(null);
  const [news, setNews] = useState([]);
  const [etf, setEtf] = useState(null);
  const [regime, setRegime] = useState(null);
  const [overlay, setOverlay] = useState({});
  const [p2stat, setP2stat] = useState('');
  const [askBusy, setAskBusy] = useState(false);
  const [q, setQ] = useState('');
  const [recent, setRecent] = useState(listRecent());

  // load everything for the code (twice for intraday after /fetch)
  const load = useCallback(async (cd, wait) => {
    setErr('');
    setDoc(null);
    pushRecent(cd);
    setRecent(listRecent());
    let d = await loadDoc(cd);
    if (d) {
      const st = await helperStatus(cd);
      const intradayOk = st && st.tfs && st.tfs['5'] && st.tfs['5'].present;
      if (!d.timeframes?.['5m']?.n && !d.timeframes?.['60m']?.n && !d.timeframes?.['15m']?.n) {
        if (st && !(st.daily?.present && st.daily.n > 0)) {
          setFetching(true);
          const res = await helperEnsure(cd);
          if (res === 'started' && wait) {
            const t0 = Date.now();
            while (Date.now() - t0 < 90000) {
              await new Promise(r => setTimeout(r, 3000));
              const s2 = await helperStatus(cd);
              if (s2 && s2.daily?.present && s2.daily.n > 0) break;
            }
            d = await loadDoc(cd);
          }
          setFetching(false);
        }
      }
    }
    if (!d) { setErr(`尚無快取 data/candles/${cd}.json（helper 抓取中或離線）`); return; }
    setDoc(d);
    const ffD = await getFundFlo();
    setFF(ffD);
    const fr = fundRow(cd, ffD);
    setName(fr ? fr.name : '');
    setRows(await getJsonl());
    setNews(await getNews(cd));
    setEtf(await getEtf('00981A'));
    setRegime(await getRegime());
  }, []);

  useEffect(() => { if (code) load(code, true); }, [code]); // eslint-disable-line

  // on open: if no fresh frozen row for today's last bar → trigger p2 (cockpit_p2.py via :8790)
  useEffect(() => {
    if (!doc || !rows.length) return;
    const last = doc.daily && doc.daily.length ? doc.daily[doc.daily.length - 1].time : null;
    const mine = rows.filter(r => r.code === code);
    const latest = mine[mine.length - 1];
    if (!latest || latest.as_of !== last) {
      setP2stat('LLM 凍結點評…');
      helperP2(code).then(() => pollP2(code));
    }
  }, [doc, rows]); // eslint-disable-line

  const pollP2 = (cd) => {
    const t0 = Date.now();
    const id = setInterval(async () => {
      if (Date.now() - t0 > 240000) { setP2stat('LLM 逾時'); clearInterval(id); return; }
      const st = await p2State(cd);
      if (st && !st.running) {
        clearInterval(id);
        setP2stat('');
        setRows(await getJsonl());
      }
    }, 5000);
  };

  const onP2 = async (cd) => {
    setP2stat('LLM 凍結點評…');
    await helperP2(cd);
    pollP2(cd);
  };

  const onAsk = async (question) => {
    setAskBusy(true);
    try {
      const fr = fundRow(code, ff);
      const out = await helperAsk(code, question, {
        tf, overlays: overlay,
        fundflo: fr ? { foreign_flow_yi: fr.foreign_flow_yi, rolling_foreign_5d_yi: fr.rolling_foreign_5d_yi, combined_flow_yi: fr.combined_flow_yi } : {},
        bars: (doc && doc.timeframes?.[tf]?.bars || doc?.daily || []).slice(-20),
      });
      return out.ok ? out.answer : (out.error || 'LLM 離線');
    } catch (e) { return 'AI 離線：' + (e.message || e); }
    finally { setAskBusy(false); }
  };

  const [tf, setTf] = useState(viewState(code).tf);
  useEffect(() => { setTf(viewState(code).tf); }, [code]); // restore per-symbol tf
  const setTfPersist = (t) => { viewState(code).tf = t; setTf(t); };
  const tog = (k) => { vs.overlays[k] = !vs.overlays[k]; setOv({ ...vs.overlays }); };
  const [ov, setOv] = useState(vs.overlays);

  if (!code) return <div className="page"><div className="err">請輸入代碼</div><Link to="/">← 返回列表</Link></div>;

  return (
    <div className="cockpit">
      <div className="cockpit-top">
        <Link to="/" className="back">← 列表</Link>
        <span className="code">{code}</span>
        <span className="nm">{name}</span>
        {fetching && <span className="pill">抓取中（Fugle/FinMind）…</span>}
        <div className="tfswitch">
          {TFS.map(t => {
            const ok = t === '1D' ? !!(doc && doc.daily?.length) : !!(doc && doc.timeframes?.[t]?.ok);
            return (
              <button key={t} className={'tfbtn' + (tf === t ? ' active' : '')} disabled={!ok}
                onClick={() => setTfPersist(t)} title={ok ? '' : '需 Fugle cache（:8790 自動抓）'}>{t}</button>
            );
          })}
        </div>
        <div className="ovtogs">
          {[['ma', 'MA'], ['macd', 'MACD'], ['piv', '支點'], ['rsi', 'RSI'], ['kd', 'KD'], ['mark', '標記'], ['draw', '畫線']].map(([k, l]) => (
            <button key={k} className={'ovbtn' + (ov[k] ? ' on' : '')} onClick={() => tog(k)}>{l}</button>
          ))}
        </div>
        <Link to={`/symbol/sepa/${code}`} className="sepalink">SEPA →</Link>
      </div>

      <div className="cockpit-body">
        <div className="left">
          <div className="card">
            <h3>搜尋 / 最近</h3>
            <div className="wl">
              <input id="wlin" placeholder="代碼 如 2454"
                onKeyDown={e => { if (e.key === 'Enter' && e.target.value.trim()) { const c = e.target.value.trim().toUpperCase(); navigate(`/symbol/${c}`); e.target.value = ''; } }} />
              <div className="wlhead muted">最近</div>
              {recent.slice(0, 8).map(c => (
                <Link key={c} className={'wlrow' + (c === code ? ' active' : '')} to={`/symbol/${c}`}>{c}</Link>
              ))}
              {ff && (ff.stocks || []).filter(s => s.code !== code).slice(0, 14).map(s => (
                <Link key={s.code} className="wlrow" to={`/symbol/${s.code}`}>{s.code} <i className="muted">{s.name}</i></Link>
              ))}
            </div>
          </div>
        </div>

        <div className="center">
          {err && <div className="err">{err}</div>}
          {!doc && !err && <div className="muted" style={{ padding: 20 }}>載入中…</div>}
          {doc && <QuoteBar code={code} doc={doc} latestRow={(rows.filter(r => r.code === code).pop()) || null} />}
          <ChartPanel code={code} doc={doc} tf={tf} overlays={ov} p2stat={p2stat} onOverlay={setOverlay} />
        </div>

        <div className="right">
          <SidebarTabs
            code={code} doc={doc} rows={rows} overlay={overlay}
            fundRow={fundRow(code, ff)} etf={etf} news={news} regime={regime}
            p2stat={p2stat} onAsk={onAsk} onP2={onP2} askBusy={askBusy}
          />
        </div>
      </div>
    </div>
  );
}
