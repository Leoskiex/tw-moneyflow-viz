import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { jget, DATA, n2 } from '../../lib/data.js';

// D3 — 台股「熱力」(學 Kansoku/AISTOCKMAP 交互，不抄美股 SPY 板塊熱力)
// Cells = topics/groups from data/TW_TOPIC_MEMBERS.json (same book as FundFlo/bubble).
// Color = FundFlo rolling_5d / momentum aggregated over the topic's members (SoT members ∩ FundFlo).
//   green = 淨流入 (up in TW money-flow terms) / red = 淨流出.
// Size = |flow| (stronger heat = bigger).  Click cell → member list → code → /symbol/:code.
// Modes align with /flow: 外資 foreign | 主動式ETF etf | 綜合 combined | 主題 screens (screens_latest themes_in/out).
// No SPY / Longbridge / US data. Topics/groups come only from TW_TOPIC_MEMBERS.json (no second map).

const MODES = [
  { k: 'foreign', l: '外資', roll: 'rolling_foreign_5d_yi', unit: '億', note: 'rolling_5d' },
  { k: 'etf', l: '主動式ETF', roll: 'etf_flow_yi', unit: '億', note: '當日（FundFlo 無 etf rolling_5d 欄位）' },
  { k: 'combined', l: '綜合', roll: 'rolling_combined_5d_yi', unit: '億', note: 'rolling_5d' },
  { k: 'screens', l: '主題進出', roll: null, unit: '主題', note: 'screens_latest themes_in/out' },
];

function heatColor(v, maxAbs) {
  if (v == null || !isFinite(v) || maxAbs <= 0) return 'rgba(148,163,184,.14)';
  const t = Math.min(1, Math.abs(v) / maxAbs);
  // green = inflow (positive), red = outflow (negative); TW: 綠進紅出
  if (v >= 0) return `rgba(34,197,94,${(0.16 + 0.66 * t).toFixed(3)})`;
  return `rgba(248,113,113,${(0.16 + 0.66 * t).toFixed(3)})`;
}

export default function HeatTw({ compact = false }) {
  const [sot, setSot] = useState(null);
  const [ff, setFF] = useState(null);
  const [scr, setScr] = useState(null);
  const [mode, setMode] = useState('foreign');
  const [sel, setSel] = useState(null); // selected topic name

  useEffect(() => {
    (async () => {
      setSot(await jget(DATA('data/TW_TOPIC_MEMBERS.json')));
      setFF(await jget(DATA('data/fundflo/latest.json')));
      setScr(await jget(DATA('data/screens_latest.json')));
    })();
  }, []);

  const model = useMemo(() => {
    if (!sot || !ff) return null;
    const ffByCode = new Map((ff.stocks || []).map(s => [s.code, s]));
    const active = MODES.find(m => m.k === mode) || MODES[0];

    // screens mode: color by themes_in (+) / themes_out (−) inst_net
    let themes = {};
    if (mode === 'screens') {
      (scr?.themes_in || []).forEach(t => { themes[t.topic] = { v: t.inst_net, src: 'in' }; });
      (scr?.themes_out || []).forEach(t => { themes[t.topic] = { v: t.inst_net, src: 'out' }; });
    }

    // aggregate per topic from FundFlo over SoT members
    const topics = Object.entries(sot).map(([key, meta]) => {
      const members = (meta.companies || []).map(c => ({
        code: c.code, name: c.name, inFF: ffByCode.has(c.code),
      }));
      const ffMembers = members.filter(m => m.inFF).map(m => ffByCode.get(m.code));
      let agg = null;
      if (active.roll) {
        const vals = ffMembers.map(s => s[active.roll] ?? null).filter(v => v != null);
        agg = vals.length ? vals.reduce((a, b) => a + b, 0) : null;
      }
      const th = themes[meta.name];
      return {
        key, name: meta.name, short: meta.shortname || meta.name, group: meta.group,
        nMembers: members.length, nFF: ffMembers.length, members,
        agg, themeV: th ? th.v : null, themeSrc: th ? th.src : null,
      };
    });
    // value for color/size: screens mode → theme inst_net; else FundFlo agg
    const valOf = (t) => (mode === 'screens' ? (t.themeV ?? t.agg) : t.agg);
    const maxAbs = Math.max(1, ...topics.map(t => Math.abs(valOf(t) || 0)));
    // group topics by their SoT group, keep order, sort by |val| desc within group
    const groups = {};
    for (const t of topics) { (groups[t.group] ||= []).push(t); }
    const groupOrder = Object.keys(groups).sort((a, b) => {
      const av = Math.max(...groups[a].map(valOf), 0);
      const bv = Math.max(...groups[b].map(valOf), 0);
      return bv - av;
    });
    return { topics, groupOrder, groups, valOf, maxAbs, unit: active.unit, mode };
  }, [sot, ff, scr, mode]);

  if (!model) {
    return <div className={`heat ${compact ? 'compact' : ''} card`}>
      <div className="muted" style={{ padding: 16 }}>載入熱力（SoT topics + FundFlo）…</div>
    </div>;
  }
  const { topics, groupOrder, groups, valOf, maxAbs, unit, mode: mMode } = model;
  const selTopic = sel ? topics.find(t => t.name === sel) : null;

  return (
    <div className={`heat ${compact ? 'compact' : ''} card`}>
      <div className="heat-head">
        <div className="heat-title">
          <h3>台股熱力</h3>
          <span className="muted" style={{ fontSize: 11 }}>
            {ff?.meta?.date || '—'} · {topics.length} 主題（SoT）· {model.unit === '億' ? 'FundFlo rolling_5d 聚合' : 'screens 主題進出'}
          </span>
        </div>
        <div className="heat-modes">
          {MODES.map(m => (
            <button key={m.k} className={'mbtn' + (mode === m.k ? ' active' : '')} onClick={() => { setMode(m.k); setSel(null); }}>{m.l}</button>
          ))}
        </div>
      </div>

      {mode === 'screens' && !scr?.themes_in?.length && !scr?.themes_out?.length && (
        <div className="muted" style={{ padding: '6px 14px', fontSize: 12 }}>本檔無 screens 主題進出 — 切回 外資/ETF/綜合 看 FundFlo 熱力。</div>
      )}

      {selTopic ? (
        <div className="heat-detail">
          <div className="heat-back" onClick={() => setSel(null)}>← {selTopic.name}（{selTopic.short}）· {selTopic.group}</div>
          <div className="heat-detail-meta">
            <span className="pill">{selTopic.nFF}/{selTopic.nMembers} 檔在 FundFlo</span>
            {selTopic.agg != null && <span className={'pill ' + (selTopic.agg >= 0 ? 'up' : 'dn')}>{unit === '億' ? n2(selTopic.agg) + ' 億 5日' : n2(selTopic.agg)}</span>}
            {selTopic.themeV != null && <span className={'pill ' + (selTopic.themeV >= 0 ? 'up' : 'dn')}>主題 {selTopic.themeSrc === 'in' ? '流入' : '流出'} {n2(selTopic.themeV)} 億</span>}
          </div>
          <div className="heat-members">
            {selTopic.members.map(m => (
              <Link key={m.code} className={'hm-row' + (m.inFF ? '' : ' dim')} to={`/symbol/${m.code}`}>
                <span className="hm-code">{m.code}</span>
                <span className="hm-name">{m.name}</span>
                {!m.inFF && <span className="muted" style={{ fontSize: 10 }}>非 FundFlo 追蹤</span>}
              </Link>
            ))}
          </div>
        </div>
      ) : (
        <div className="heat-grid">
          {groupOrder.map(g => (
            <div className="heat-group" key={g}>
              <div className="heat-group-label">{g}</div>
              <div className="heat-cells">
                {groups[g].map(t => {
                  const v = valOf(t);
                  const size = 40 + 60 * (Math.abs(v || 0) / maxAbs);
                  const label = v == null ? '—' : (v >= 0 ? '+' : '') + (unit === '億' ? n2(v) + '億' : String(Math.round(v)));
                  return (
                    <button key={t.key} className="heat-cell" onClick={() => setSel(t.name)}
                      style={{ background: heatColor(v, maxAbs), minWidth: size + 'px' }}
                      title={`${t.name} · ${t.nFF}/${t.nMembers} 檔 · ${label}`}>
                      <span className="hc-name">{t.short}</span>
                      <span className={'hc-val ' + (v != null ? (v >= 0 ? 'up' : 'dn') : 'muted')}>{label}</span>
                      <span className="hc-n muted">{t.nFF}/{t.nMembers}</span>
                    </button>
                  );
                })}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="heat-foot muted">
        台＝錢／題材（FundFlo 法人 + SoT 主題聚合，點格子進個股）；≠ 美股 SPY 板塊熱力（指數權重）。綠＝淨流入、紅＝淨流出。資料：TW_TOPIC_MEMBERS.json + fundflo/latest.json{mode === 'screens' ? ' + screens_latest.json' : ''}。
      </div>
    </div>
  );
}
