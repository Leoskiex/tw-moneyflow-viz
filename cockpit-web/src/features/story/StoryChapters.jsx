import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { plain, stateClass, loadStory } from '../../lib/story.js';

const esc = (s) => String(s ?? '');
const fmt = (n, d = 1) => (n == null || Number.isNaN(+n)) ? '—' : Number(n).toFixed(d);
const signedYi = (n) => {
  if (n == null || Number.isNaN(+n)) return '—';
  const v = Number(n);
  return (v > 0 ? '多買 ' : '多賣 ') + Math.abs(v).toFixed(1) + ' 億';
};
const clsNum = (n) => (n > 0 ? 'pos' : n < 0 ? 'neg' : '');

// 五章「今日故事」— ported from :8777/index.html, reading the SAME day-end JSON.
// Clicking a code/name deep-links into /symbol/:code (keep code, no second site).
export default function StoryChapters({ ff }) {
  const [st, setSt] = useState(null);
  useEffect(() => { loadStory().then(setSt); }, []);
  if (!st) return <div className="story"><div className="muted" style={{ padding: 12 }}>故事資料載入中…</div></div>;
  return (
    <div className="story">
      <div className="story-disc">這是用規則拼出來的小故事，不是保證賺錢。錢少就跟著大錢喝一點湯，不要追最吵的那一下。</div>
      <nav className="story-toc" aria-label="章節">
        {['ch1:今天怎樣', 'ch2:錢怎麼走', 'ch3:哪裡變熱', 'ch4:我怎麼辦', 'ch5:別亂追'].map(x => {
          const [id, lab] = x.split(':');
          return <button key={id} className="tocbtn" onClick={() => { const el = document.getElementById(id); if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' }); }}>{lab}</button>;
        })}
      </nav>

      <Ch1 brief={st.brief} digest={st.digest} date={dateOf(st)} />
      <Ch2 brief={st.brief} streaks={st.streaks} />
      <Ch3 themes={st.themes} />
      <Ch4 playbooks={st.playbooks} radar={st.radar} streaks={st.streaks} />
      <Ch5 scoreboard={st.scoreboard} />
      <div className="story-foot muted">先讀故事，再決定要不要點進圖。資料日期看最上面。</div>
    </div>
  );
}

function dateOf(st) {
  return (st.brief && st.brief.date) || (st.digest && st.digest.date) || (st.radar && st.radar.date) || '—';
}

function Ch1({ brief, digest, date }) {
  const headline = plain((brief && brief.headline) || (digest && digest.headline) || '—');
  const one = plain((brief && brief.one_liner) || (digest && digest.one_liner) || '');
  const sec = (brief && brief.sections || []).find(s => s.id === 'verdict') || (brief && brief.sections || [])[0];
  const lines = (sec && sec.lines) || (brief && brief.evidence_raw) || [];
  return (
    <section className="chapter" id="ch1">
      <div className="eyebrow">第 1 段 · 資料日期 {date}</div>
      <h2>今天市場怎樣了？</h2>
      <div className={'hero ' + stateClass(headline)}>{headline}</div>
      <p className="lede">{one}</p>
      <ul className="lines">{lines.slice(0, 5).map((l, i) => <li key={i}>{plain(l)}</li>)}</ul>
      <div className="deep"><Link to="/research">看完整日報 →</Link></div>
    </section>
  );
}

function Ch2({ brief, streaks }) {
  const m = (brief && brief.metrics) || {};
  const kpis = [
    ['外國叔叔的錢', m.foreign, '外國來的買賣', false],
    ['基金老師的錢', m.trust, '臺灣基金買賣', false],
    ['券商自己的錢', m.dealer, '證券公司買賣', false],
    ['當天衝來衝去', m.daytrade_pct, '越高原來越吵', true],
    ['借錢做多變多少', m.margin_delta, '融資增減', false],
    ['漲／跌家數', (m.advance != null && m.decline != null) ? (m.advance + '／' + m.decline) : null, '市場寬不寬', true],
  ];
  const flowSec = (brief && brief.sections || []).find(s => s.id === 'flow');
  const flowLines = (flowSec && flowSec.lines) || (brief && brief.bullets) || [];
  const top = streaks && streaks.top || {};
  const fb = (top.foreign_buy_streak || []).slice(0, 4);
  const tb = (top.trust_buy_streak || []).slice(0, 3);
  const st = streaks && streaks.stats || {};
  return (
    <section className="chapter" id="ch2">
      <div className="eyebrow">第 2 段</div>
      <h2>錢往哪裡走？</h2>
      <div className="kpis">{kpis.map(([lab, v, hint, isPct], i) => {
        const show = lab.indexOf('家數') >= 0 ? (v || '—') : (isPct ? (v == null ? '—' : fmt(v, 1) + '%') : signedYi(v));
        const cls = (typeof v === 'number' && lab.indexOf('家數') < 0 && !isPct) ? clsNum(v) : '';
        return <div key={i} className="kpi"><div className="l">{lab}</div><div className={'v ' + cls}>{show}</div><div className="hint">{hint}</div></div>;
      })}</div>
      <ul className="lines">{flowLines.slice(0, 4).map((l, i) => <li key={i}>{plain(l)}</li>)}</ul>
      {fb.length > 0 && (
        <div className="streaks">
          <div className="t">誰連續買了好幾天？</div>
          <div className="d">外國錢連買滿 3 天以上約 <b>{st.foreign_buy_ge3 ?? '—'}</b> 家；基金連買滿 3 天以上約 <b>{st.trust_buy_ge3 ?? '—'}</b> 家。</div>
          <div className="d">
            <b>外國錢一直買：</b>{fb.map(r => <Link key={r.code} to={`/symbol/${r.code}`}>{r.code} {r.name || ''} <i className="muted">連 {r.streak} 天</i></Link>)}
          </div>
          {tb.length > 0 && <div className="d"><b>基金一直買：</b>{tb.map(r => <Link key={r.code} to={`/symbol/${r.code}`}>{r.code} {r.name || ''} <i className="muted">連 {r.streak} 天</i></Link>)}</div>}
        </div>
      )}
    </section>
  );
}

function Ch3({ themes }) {
  const acc = (themes && themes.themes || []).filter(t => t.flags && t.flags.accelerating).slice(0, 6);
  const dec = (themes && themes.themes || []).filter(t => t.flags && t.flags.decelerating).slice(0, 4);
  const frag = (themes && themes.themes || []).filter(t => t.flags && t.flags.fragile_inflow).slice(0, 3);
  const top = acc[0];
  return (
    <section className="chapter" id="ch3">
      <div className="eyebrow">第 3 段</div>
      <h2>哪裡變熱？哪裡變冷？</h2>
      <div className="two">
        <div><div className="eyebrow">變熱（錢加速進來）</div>
          <div className="chips">{acc.length ? acc.map(t => <span key={t.id} className="chip hot">{t.shortname || t.name}</span>) : <span className="chip">（暫無）</span>}</div>
        </div>
        <div><div className="eyebrow">變冷／假熱鬧</div>
          <div className="chips">{[...dec, ...frag].length
            ? [...dec, ...frag].map(t => <span key={t.id} className={'chip ' + (t.flags && t.flags.fragile_inflow ? 'fragile' : 'cold')}>{t.shortname || t.name}{t.flags && t.flags.fragile_inflow ? ' · 假熱鬧' : ''}</span>)
            : <span className="chip">（暫無）</span>}</div>
        </div>
      </div>
      <p className="lede">{top ? `現在最顯眼變熱的是「${top.shortname || top.name}」。如果熱度只在老大身上，老二老三不一定還有湯喝。` : '今天題材冷熱不明顯，先回頭看天氣和錢怎麼走。'}</p>
    </section>
  );
}

function Ch4({ playbooks, radar, streaks }) {
  const pbs = (playbooks && playbooks.playbooks) || [];
  const script = plain((playbooks && playbooks.daily_script) || '先看天氣。可以喝湯就小小喝；假動作就躲開。');
  const lists = (radar && radar.lists) || {};
  const streakMap = {};
  if (streaks && streaks.top) for (const k of Object.keys(streaks.top)) for (const r of (streaks.top[k] || [])) { (streakMap[r.code] ||= { code: r.code, name: r.name })[k] = r.streak; }
  const withStreak = (rows) => (rows || []).map(r => Object.assign({}, r, streakMap[r.code] || {}));
  const focus = withStreak(lists.focus_list).slice(0, 5);
  const caution = withStreak(lists.caution_list).slice(0, 5);
  return (
    <section className="chapter" id="ch4">
      <div className="eyebrow">第 4 段</div>
      <h2>那我今天怎麼辦？</h2>
      <p className="lede">{script}</p>
      <div className="pb">{pbs.map(p => {
        const danger = String(p.action || '').indexOf('躲開') >= 0;
        const do0 = plain((Array.isArray(p.do) && p.do[0]) || (p.gate && p.gate.description) || '');
        return <div key={p.id} className={'card-mini ' + (danger ? 'bad' : 'good')}><div className="t">{plain(p.action)} · {plain(p.name)}</div><div className="d">{String(do0).slice(0, 160)}</div><div className="fail">什麼時候不算數：{plain(p['失效'] || '—')}</div></div>;
      })}
        {pbs.length === 0 && <div className="lede">還沒有小抄</div>}
      </div>
      <div className="two">
        <div><div className="eyebrow">可以喝一點湯</div>{stockRows(focus)}</div>
        <div><div className="eyebrow">先躲開</div>{stockRows(caution)}</div>
      </div>
      <div className="deep"><Link to="/live">看盤中 Live →</Link> · <Link to="/research">進階研究 →</Link></div>
    </section>
  );
}

function stockRows(rows) {
  if (!rows || !rows.length) return <div className="lede">（今天這欄暫時沒有）</div>;
  return rows.map(r => {
    const bits = [];
    if (r.foreign_buy_streak > 0) bits.push('外國錢連買 ' + r.foreign_buy_streak + ' 天');
    if (r.foreign_sell_streak > 0) bits.push('外國錢連賣 ' + r.foreign_sell_streak + ' 天');
    if (r.trust_buy_streak > 0) bits.push('基金連買 ' + r.trust_buy_streak + ' 天');
    const extra = bits.length ? bits.join('；') : plain((r.suggested_action || r.topic || '').slice(0, 36));
    return (
      <div key={r.code} className="stock">
        <div>
          <Link to={`/symbol/${r.code}`} className="code">{r.code}</Link>{' '}
          <Link to={`/symbol/${r.code}`} className="name">{r.name || ''}</Link>{' '}
          <Link to={`/symbol/sepa/${r.code}`} className="mini">SEPA</Link>
        </div>
        <div className="act">{extra}</div>
      </div>
    );
  });
}

function Ch5({ scoreboard }) {
  const by = {};
  for (const r of (scoreboard && scoreboard.rows) || []) by[r.signal_type] = r;
  const order = ['fake_thrust', 'chase_first_bar', 'second_wave', 'distribution_detector', 'institutional_accumulation'];
  const labels = {
    fake_thrust: '假動作 → 優先躲開', chase_first_bar: '追第一下衝很高 → 比較常付錢',
    second_wave: '洗盤後再往上的第二波 → 可當濾鏡，不是保證',
    distribution_detector: '大錢可能在倒貨', institutional_accumulation: '機構慢慢買（樣本裡還不夠好）',
  };
  return (
    <section className="chapter" id="ch5">
      <div className="eyebrow">第 5 段</div>
      <h2>哪些不要亂追？</h2>
      <div className="pb">{order.filter(k => by[k]).map(k => {
        const r = by[k]; const ex = r.stats && r.stats.mean_excess_5d;
        const bad = ex != null && ex < 0; const pct = ex == null ? '—' : ((ex * 100).toFixed(1) + '%');
        return <div key={k} className={'card-mini ' + (bad ? 'bad' : 'good')}><div className="t">{labels[k] || k}</div><div className="d">以前這招後面五天平均大約 {pct}。看過大約 {r.stats && r.stats.N || '—'} 次。</div></div>;
      })}
        {Object.keys(by).length === 0 && <div className="lede">還沒有紅燈表</div>}
      </div>
      <div className="deep"><Link to="/research">看進階分數 →</Link></div>
    </section>
  );
}
