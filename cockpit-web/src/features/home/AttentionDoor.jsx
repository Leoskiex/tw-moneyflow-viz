import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { getFundFlo, jget, DATA } from '../../lib/data.js';

// WAVE 1 / A1 — attention door: 3–5 one-click symbols + ≤3 What-changed cards.
// Dad-test <10s: date/regime → why → pick a symbol.

const MAX_PICKS = 5;
const DECISION_ZH = {
  BUY_ON_CONFIRMATION: '等確認買',
  BUY_CONFIRM: '確認買',
  HOLD: '抱住',
  WAIT_PULLBACK: '等回撤',
  REDUCE: '減碼',
  EXIT: '出場',
  AVOID: '避開',
  WATCH: '觀察',
};

function trunc(s, n = 72) {
  const t = (s || '').toString().trim();
  if (!t) return '';
  return t.length > n ? t.slice(0, n - 1) + '…' : t;
}

function labelAction(row) {
  const raw = row.action_flat || row.decision || '';
  return DECISION_ZH[raw] || DECISION_ZH[row.decision] || raw || '—';
}

/** Prefer entry_ready opportunities (by cmi desc), else soft_gate_book by target_weight then cmi. */
export function pickFocusSymbols(dayOp, fundflo, limit = MAX_PICKS) {
  const seen = new Set();
  const out = [];

  const push = (row, source) => {
    const code = String(row.symbol || row.code || '').trim();
    if (!code || seen.has(code) || out.length >= limit) return;
    seen.add(code);
    out.push({
      code,
      name: row.name || '',
      decision: row.decision || '',
      action_flat: row.action_flat || '',
      cmi: row.cmi != null ? Number(row.cmi) : null,
      entry_ready: !!row.entry_ready,
      source,
    });
  };

  const opps = Array.isArray(dayOp?.opportunities) ? [...dayOp.opportunities] : [];
  const ready = opps.filter((o) => o && o.entry_ready);
  ready.sort((a, b) => (Number(b.cmi) || 0) - (Number(a.cmi) || 0));
  for (const o of ready) push(o, 'entry_ready');

  if (out.length < limit) {
    const book = Array.isArray(dayOp?.soft_gate_book) ? [...dayOp.soft_gate_book] : [];
    book.sort((a, b) => {
      const tw = (Number(b.target_weight) || 0) - (Number(a.target_weight) || 0);
      if (tw !== 0) return tw;
      return (Number(b.cmi) || 0) - (Number(a.cmi) || 0);
    });
    for (const o of book) push(o, 'soft_gate');
  }

  // FundFlo fallback when Day Op thin/missing
  if (out.length < limit) {
    const stocks = Array.isArray(fundflo?.stocks) ? fundflo.stocks : [];
    for (const s of stocks) {
      push({ symbol: s.code, name: s.name, decision: 'WATCH', action_flat: 'WATCH' }, 'fundflo');
      if (out.length >= limit) break;
    }
  }

  return out;
}

function buildCards({ ff, regime, dayOp, picks }) {
  const w = dayOp?.weather || {};
  const date = ff?.meta?.date || dayOp?.as_of_spectrum || dayOp?.as_of_regime || '—';
  const regimeLabel =
    regime?.primary_label ||
    w.regime_label ||
    w.regime ||
    '—';

  const why = trunc(w.headline || w.action || '', 90) || '今日尚無 Day Op 天氣摘要';

  const top = picks[0];
  const investigateTo = top ? `/symbol/${top.code}` : '/symbol';
  const investigateLabel = top
    ? `看 ${top.code} ${top.name || ''}`.trim()
    : '打開個股搜尋';

  return [
    {
      key: 'what',
      tag: 'What',
      title: '今天是什麼局',
      body: `${date} · 市況 ${regimeLabel}`,
    },
    {
      key: 'why',
      tag: 'Why',
      title: '為什麼這樣看',
      body: why,
    },
    {
      key: 'investigate',
      tag: 'Investigate',
      title: '下一步點哪',
      body: investigateLabel,
      to: investigateTo,
    },
  ];
}

export default function AttentionDoor({ fundflo, regime }) {
  const [dayOp, setDayOp] = useState(null);
  const [ffLocal, setFfLocal] = useState(fundflo || null);

  useEffect(() => {
    jget(DATA('data/cmi/day_operator_latest.json')).then(setDayOp);
  }, []);

  useEffect(() => {
    if (fundflo) {
      setFfLocal(fundflo);
      return;
    }
    getFundFlo().then(setFfLocal);
  }, [fundflo]);

  const picks = useMemo(
    () => pickFocusSymbols(dayOp, ffLocal, MAX_PICKS),
    [dayOp, ffLocal],
  );

  const cards = useMemo(
    () => buildCards({ ff: ffLocal, regime, dayOp, picks }),
    [ffLocal, regime, dayOp, picks],
  );

  return (
    <section className="attention-door" aria-label="今日焦點">
      <div className="ad-head">
        <h2 className="ad-title">今日焦點</h2>
        <span className="ad-sub muted">
          {dayOp ? 'Day Op 一鍵標的' : 'FundFlo 備援'}
          {picks.length ? ` · ${picks.length} 檔` : ''}
        </span>
      </div>

      <div className="ad-picks">
        {picks.length === 0 && (
          <div className="ad-empty muted">尚無焦點標的（Day Op / FundFlo 都空）</div>
        )}
        {picks.map((p) => (
          <Link key={p.code} className="ad-pick" to={`/symbol/${p.code}`}>
            <span className="ad-code">{p.code}</span>
            <span className="ad-name">{p.name || '—'}</span>
            <span className="ad-act">{labelAction(p)}</span>
            {p.cmi != null && Number.isFinite(p.cmi) && (
              <span className="ad-cmi muted">CMI {Math.round(p.cmi)}</span>
            )}
            {p.entry_ready && <span className="ad-ready">可進</span>}
          </Link>
        ))}
      </div>

      <div className="ad-cards">
        {cards.map((c) => (
          <div key={c.key} className={'ad-card ad-' + c.key}>
            <div className="ad-card-tag">{c.tag}</div>
            <div className="ad-card-title">{c.title}</div>
            {c.to ? (
              <Link className="ad-card-body ad-card-link" to={c.to}>{c.body} →</Link>
            ) : (
              <div className="ad-card-body">{c.body}</div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
