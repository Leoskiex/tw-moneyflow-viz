import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { jget, DATA } from '../lib/data.js';

// 看圖版 (F11) — board.html port on the SAME FundFlo book (no second topic map):
// theme_rotation/latest.json (accelerating / decelerating / fragile_inflow + flags)
// + scoreboard/latest.json summary. Legacy board.html used MF_SAMPLE (invented) —
// this reads the real day-end JSON instead.
export default function BoardPage() {
  const [themes, setThemes] = useState(null);
  const [board, setBoard] = useState(null);
  useEffect(() => {
    jget(DATA('data/theme_rotation/latest.json')).then(setThemes);
    jget(DATA('data/scoreboard/latest.json')).then(setBoard);
  }, []);

  if (!themes) return <div className="page boardpage"><div className="muted" style={{ padding: 16 }}>看圖版載入中…</div></div>;

  const cols = [
    ['accelerating', '加速中', 'up'],
    ['decelerating', '減速中', 'dn'],
    ['fragile_inflow', '脆弱流入', 'warn'],
  ];

  return (
    <div className="page boardpage">
      <div className="fb-top">
        <div>
          <div className="hs">看圖版 · 題材輪動</div>
          <div className="muted">theme_rotation（FundFlo 同書）· {themes.meta?.date || themes.date || '—'} · 非第二本題材表</div>
        </div>
        <Link className="pill" to="/">← 回今日</Link>
      </div>

      {board && (
        <div className="board-kpis muted">
          <span>signals {board.signals_date || '—'}</span>
          <span>base rate {board.base_rate != null ? board.base_rate : '—'}</span>
          <span>events joined {board.n_events_joined ?? '—'}</span>
        </div>
      )}

      <div className="board-cols">
        {cols.map(([key, label, tone]) => {
          const items = themes[key] || [];
          return (
            <div className={'bcol ' + tone} key={key}>
              <h4>{label} <span className="muted">{items.length}</span></h4>
              <div className="bcol-list">
                {items.length === 0 && <div className="muted">（無）</div>}
                {items.map((t, i) => {
                  const name = typeof t === 'string' ? t : (t.name || t.topic || t.id);
                  const code = (typeof t === 'object' && t.code) ? t.code : null;
                  return code
                    ? <Link key={i} to={`/symbol/${code}`}>{name}</Link>
                    : <span key={i}>{name}</span>;
                })}
              </div>
            </div>
          );
        })}
      </div>

      {themes.themes && Array.isArray(themes.themes) && (
        <div className="board-flags">
          <h4>題材旗標 <span className="muted">{themes.flag_counts ? Object.values(themes.flag_counts).reduce((a, b) => a + (b || 0), 0) : ''}</span></h4>
          <div className="flaglist">
            {themes.themes.slice(0, 30).map((t, i) => (
              <span key={i} className={'flag ' + (t.flag === 'accelerating' ? 'up' : t.flag === 'decelerating' ? 'dn' : 'muted')}>
                {t.name || t.id || t.topic}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
