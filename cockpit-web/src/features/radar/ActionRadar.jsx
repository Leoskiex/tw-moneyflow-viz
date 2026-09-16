import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { jget, DATA } from '../../lib/data.js';

// 動作雷達 (F09) — port of action-radar.html reading the SAME action_radar_latest.json.
// name/code click → /symbol/:code. No LLM, no second site.
const LIST_META = [
  ['focus_list', '焦點 focus', 'up'],
  ['caution_list', '謹慎 caution', 'warn'],
  ['fresh_stop', '新鮮止跌', 'accent'],
  ['accel_now', '加速修復', 'up'],
  ['washout_stop', '洗盤止跌', 'accent'],
  ['repairing', '修復中', 'muted'],
];

function rowOf(x) {
  // builder rows may be objects {code,name,...} or plain codes
  if (typeof x === 'string' || typeof x === 'number') return { code: String(x).padStart(4, '0'), name: '' };
  return { code: String(x.code || '').padStart(4, '0'), name: x.name || '', why: x.why || x.reason || '' };
}

export default function ActionRadar() {
  const [d, setD] = useState(null);
  useEffect(() => { jget(DATA('data/action_radar_latest.json')).then(setD); }, []);
  if (!d) return <div className="radar"><div className="muted" style={{ padding: 12 }}>雷達載入中…</div></div>;

  const macro = d.macro || {};
  return (
    <div className="radar">
      <div className="radar-head">
        <h3>動作雷達 <span className="muted">（{d.date}）</span></h3>
        <div className="muted" style={{ fontSize: 11 }}>{d.disclaimer || ''}</div>
      </div>
      {macro.actions_macro != null && (
        <div className="radar-macro">
          {macro.macro_state && <span className="pill">市況 {macro.macro_state}</span>}
          {Array.isArray(macro.actions_macro) ? (
            <span className="muted">{macro.actions_macro.map((a, i) => (
              <span key={i}>{typeof a === 'string' ? a : a.title}
                {a && a.detail ? <em className="muted">（{String(a.detail).slice(0, 60)}）</em> : null}
                {i < macro.actions_macro.length - 1 ? '；' : ''}
              </span>
            ))}</span>
          ) : (
            <span className="muted">{String(macro.actions_macro)}</span>
          )}
        </div>
      )}
      <div className="radar-grid">
        {LIST_META.map(([key, label, tone]) => {
          const items = (d.lists?.[key] || []).map(rowOf).filter(r => r.code);
          if (!items.length) return null;
          return (
            <div className={'rcard ' + tone} key={key}>
              <h4>{label} <span className="muted">{items.length}</span></h4>
              <div className="rcard-list">
                {items.slice(0, 12).map((r, i) => (
                  <Link key={i} to={`/symbol/${r.code}`} className="rcard-row">
                    <span className="rcard-code">{r.code}</span>
                    <span className="rcard-name">{r.name}</span>
                    {r.why && <span className="rcard-why muted">{String(r.why).slice(0, 40)}</span>}
                  </Link>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
