import { useEffect, useState } from 'react';
import { jget, DATA } from '../../lib/data.js';

// D8 — CMI 天氣 badge on 今日. Thin badge only (X01web in FUNCTION_DATA_MATRIX):
// reads data/cmi/day_operator_latest.json (already copied to the served tree).
// Shows weather.mode + as_of + headline/action; click → thin panel with
// cash_target / allow_new_entries / foreign_net_yi / adv_ratio / regime.
// No MCPT / STRATEGY_BOOK / FULLSPEC tables. Missing file → empty state.
const MODE_TONE = { NORMAL: 'neu', DEFENSIVE: 'warn', CRASH_DEFENSE: 'bad', RE_ENTER: 'good' };
const fmtYi = (v) => (v == null || !Number.isFinite(v)) ? '—' : ((v >= 0 ? '+' : '') + v.toFixed(1) + ' 億');

export default function CmiBadge() {
  const [d, setD] = useState(null);
  const [open, setOpen] = useState(false);
  useEffect(() => { jget(DATA('data/cmi/day_operator_latest.json')).then(setD); }, []);

  if (!d) return (
    <div className="cmibadge">
      <div className="cmi-pill muted">CMI 天氣 — 尚無資料</div>
      <div className="cmi-sub muted">Day Operator JSON 缺時顯示空態；資料到位後自動顯示。</div>
    </div>
  );

  const w = d.weather || {};
  const tone = MODE_TONE[w.mode] || 'neu';
  const asOf = d.as_of_spectrum || (w.as_of) || '—';

  return (
    <div className="cmibadge">
      <button className={'cmi-pill ' + tone} onClick={() => setOpen(o => !o)} aria-expanded={open}>
        <span className="cmi-dot" />
        <span className="cmi-mode">{w.mode || '—'}</span>
        <span className="cmi-weather-label muted">CMI 天氣</span>
        <span className="cmi-asof muted">{asOf}</span>
        <span className="cmi-headline">{w.headline || ''}</span>
      </button>
      {open && (
        <div className="cmi-panel">
          <div className="cmi-kv">
            <div><span className="k">行動</span><span className="v">{w.action || '—'}</span></div>
            <div><span className="k">現金目標</span><span className="v">{w.cash_target != null ? Math.round(w.cash_target * 100) + '%' : '—'}</span></div>
            <div><span className="k">允許新開</span><span className={'v ' + (d.allow_new_entries === false ? 'dn' : 'up')}>{d.allow_new_entries == null ? '—' : (d.allow_new_entries ? '是' : '否')}</span></div>
            <div><span className="k">外資淨額</span><span className={'v ' + (w.foreign_net_yi > 0 ? 'up' : w.foreign_net_yi < 0 ? 'dn' : '')}>{fmtYi(w.foreign_net_yi)}</span></div>
            <div><span className="k">ADV 比</span><span className="v">{w.adv_ratio != null ? w.adv_ratio.toFixed(2) : '—'}</span></div>
            <div><span className="k">Regime</span><span className="v">{w.regime_label || w.regime || '—'}</span></div>
          </div>
          <div className="cmi-foot muted">
            來源：CMI Day Operator（consume-only；本站只讀，不回寫）。as_of {asOf}
            {d.as_of_regime && d.as_of_regime !== asOf ? ` · regime 數據 as_of ${d.as_of_regime}` : ''}
          </div>
        </div>
      )}
    </div>
  );
}
