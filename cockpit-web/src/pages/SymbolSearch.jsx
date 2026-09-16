import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getFundFlo, loadDoc } from '../lib/data.js';
import { listRecent } from '../lib/symbolStore.js';

const norm = (s) => String(s ?? '').toUpperCase().replace(/[^A-Z0-9]/g, '');

// 個股 tab — type a code/name, go /symbol/:code (keep code). Also lists recent
// + FundFlo-followed names. No whole-market list (that's the 水流排行 on 今日).
export default function SymbolSearch() {
  const navigate = useNavigate();
  const [q, setQ] = useState('');
  const [ff, setFF] = useState(null);
  const [docs, setDocs] = useState([]); // {code,name} for name-search over followed/recent
  useEffect(() => {
    getFundFlo().then(setFF);
    const codes = [];
    try { codes.push(...listRecent()); } catch (_) {}
    if (ff) for (const s of (ff.stocks || []).slice(0, 40)) codes.push(s.code);
    const uniq = [...new Set(codes.map(c => String(c).toUpperCase()))];
    (async () => {
      const out = [];
      for (const c of uniq.slice(0, 24)) {
        const d = await loadDoc(c);
        if (d && d.meta && d.meta.name) out.push({ code: c, name: d.meta.name });
      }
      setDocs(out);
    })();
  }, [ff]);

  const results = useMemo(() => {
    const nq = norm(q);
    if (!nq) return [];
    const seen = new Set();
    const out = [];
    for (const s of (ff?.stocks || [])) {
      if (norm(s.code).includes(nq) || norm(s.name).includes(nq)) {
        if (!seen.has(s.code)) { seen.add(s.code); out.push({ code: s.code, name: s.name, source: 'fundflo' }); }
      }
    }
    for (const s of docs) {
      if (norm(s.code).includes(nq) || norm(s.name).includes(nq)) {
        if (!seen.has(s.code)) { seen.add(s.code); out.push(s); }
      }
    }
    return out.slice(0, 12);
  }, [q, ff, docs]);

  const go = (code) => { navigate(`/symbol/${code}`); };
  const onKeyDown = (e) => {
    if (e.key !== 'Enter') return;
    const nq = norm(q);
    if (!nq) return;
    if (/^[0-9]{4}$/.test(nq)) return go(nq);
    const hit = results.find(r => norm(r.code) === nq || norm(r.name) === nq) || results[0];
    if (hit) go(hit.code);
  };

  const recent = listRecent();
  const followed = (ff?.stocks || []).slice(0, 12);

  return (
    <div className="page symsearch">
      <div className="topstrip">
        <div>
          <div className="hs">個股</div>
          <div className="muted">輸入代號（如 2454）或名稱，Enter 直達駕駛艙</div>
        </div>
      </div>
      <div className="card" style={{ marginBottom: 12 }}>
        <input className="ss-input" placeholder="代號 2454 / 名稱 聯發科" value={q} autoFocus
          onChange={e => setQ(e.target.value)} onKeyDown={onKeyDown} />
        {results.length > 0 && (
          <div className="ss-results">
            {results.map(r => (
              <div key={r.code} className="ss-row" onClick={() => go(r.code)}>
                <span className="bc">{r.code}</span><span className="bn muted">{r.name}</span>
                <span className="muted">→ /symbol/{r.code}</span>
              </div>
            ))}
          </div>
        )}
      </div>
      {recent.length > 0 && (
        <div className="card">
          <h3>最近</h3>
          <div style={{ padding: 10, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {recent.map(c => <Link key={c} className="chip" to={`/symbol/${c}`}>{c}</Link>)}
          </div>
        </div>
      )}
      <div className="card">
        <h3>水流追蹤（FundFlo 前 12）</h3>
        <div style={{ padding: 10, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          {followed.map(s => (
            <Link key={s.code} className="chip" to={`/symbol/${s.code}`}>
              {s.code} {s.name}
            </Link>
          ))}
        </div>
      </div>
    </div>
  );
}
