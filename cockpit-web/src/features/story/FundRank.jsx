import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { getFundFlo } from '../../lib/data.js';
import { RANK_MODES, rankRows, modePopulated } from '../../lib/story.js';

const fmtYi = (v) => (v == null || !Number.isFinite(v)) ? '—' : ((v >= 0 ? '+' : '') + v.toFixed(2) + ' 億');
const fmtPct = (v) => (v == null || !Number.isFinite(v)) ? '—' : ((v >= 0 ? '+' : '') + v.toFixed(2) + '%');
const cls = (v) => (v > 0 ? 'up' : v < 0 ? 'dn' : '');

// 錢怎麼流 · 水流排行 — ported from :8777/fund-flow.html, reading the same
// data/fundflo/latest.json. Click a code/name → /symbol/:code (keep code).
export default function FundRank() {
  const [ff, setFF] = useState(null);
  const [mode, setMode] = useState('foreign');
  const [dir, setDir] = useState('both');
  const [count, setCount] = useState(15);
  useEffect(() => { getFundFlo().then(setFF); }, []);

  const stocks = (ff && ff.stocks) || [];
  // etf rolling is often absent in the slim — only offer a mode if it has data.
  const modes = RANK_MODES.filter(m => modePopulated(stocks, m.id));
  const effMode = modes.some(m => m.id === mode) ? mode : (modes[0] ? modes[0].id : 'foreign');
  const rows = useMemo(() => rankRows(stocks, effMode, dir, count), [stocks, effMode, dir, count]);
  const m = RANK_MODES.find(x => x.id === effMode) || RANK_MODES[0];

  return (
    <div className="fundrank">
      <div className="fr-head">
        <div className="fr-title">
          <h3>錢怎麼流 · 水流排行 <span className="muted">（{ff && ff.meta && ff.meta.date ? ff.meta.date : '—'}）</span></h3>
          <div className="muted" style={{ fontSize: 11 }}>近 5 日滾動（億） · 點名稱進個股 / SEPA</div>
        </div>
        <div className="fr-ctrl">
          <div className="fr-modes">{modes.map(x => <button key={x.id} className={'mbtn' + (effMode === x.id ? ' on' : '')} onClick={() => { setMode(x.id); setDir('both'); }}>{x.label}</button>)}</div>
          <div className="fr-modes">
            {effMode === 'turnover' ? null : (
              <>
                <select value={dir} onChange={e => setDir(e.target.value)} aria-label="方向">
                  <option value="both">兩邊都看</option><option value="buy">進來最多</option><option value="sell">出去最多</option>
                </select>
              </>
            )}
            <select value={count} onChange={e => setCount(Number(e.target.value))} aria-label="筆數">
              {[10, 15, 20, 30].map(n => <option key={n} value={n}>{n}</option>)}
            </select>
          </div>
        </div>
      </div>
      <div className="fr-list">
        {rows.length === 0 && <div className="muted" style={{ padding: 10 }}>此模式暂无資料（slim 未收錄）</div>}
        {rows.map(r => (
          <div key={r.code} className="fr-row">
            <div className="fr-l">
              <Link to={`/symbol/${r.code}`} className="fr-code">{r.code}</Link>
              <Link to={`/symbol/sepa/${r.code}`} className="fr-name">{r.name}</Link>
              <span className="fr-sub muted">{m.daily ? `${effMode === 'combined' ? '綜合當日' : effMode === 'etf' ? 'ETF 當日' : '外資當日'} ${fmtYi(r.daily)}` : ''}</span>
            </div>
            <div className="fr-vals">
              <div className={'fr-v ' + cls(r.rolling)}>{fmtYi(r.rolling)}</div>
              <div className="fr-v muted">{r.momentum != null ? '動能 ' + fmtYi(r.momentum) : ''}</div>
              <div className={'fr-v ' + cls(r.ret)}>{fmtPct(r.ret)}</div>
            </div>
          </div>
        ))}
      </div>
      <div className="fr-key muted">紅＝近5日流入 / 股價漲；綠＝流出 / 跌。單位：億元。</div>
    </div>
  );
}
