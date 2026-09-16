import { useEffect, useRef, useState } from 'react';
import { n2, mdToHtml, comments, reassessStart, reassessStatus, explain, STANCE_LABEL, STANCE_TONE, historyRows, noteGet, noteSet, jraw, DATA, helperNews } from '../../lib/data.js';
import SymbolMemory from './SymbolMemory.jsx';

// Right rail — 预测 · 环境 · 消息 · 复盘 · AI点评 + docked ChatDock (及時 AI).
// Tab set mirrors kansoku features/cockpit/sharedSidebarTabs.tsx (prediction/env/news/review/ai),
// filled from our TW data: cockpit.jsonl, FundFlo, news, 0050 RS.
export default function SidebarTabs({ code, doc, rows, overlay, fundRow, etf, news, regime, p2stat, onAsk, onP2, askBusy }) {
  const [tab, setTab] = useState('predict');
  const bodyRef = useRef(null);
  const [newsList, setNewsList] = useState([]);
  const [newsBusy, setNewsBusy] = useState(false);
  const [newsErr, setNewsErr] = useState('');

  // load cached news (data/news/<code>.json via :8778) on code change
  useEffect(() => { setNewsList(news || []); setNewsErr(''); }, [code]); // eslint-disable-line
  const fetchNews = async (force) => {
    setNewsBusy(true); setNewsErr('');
    const r = await helperNews(code, force);
    setNewsBusy(false);
    if (r && r.ok) { setNewsList(r.items || []); }
    else if (r && r.error) { setNewsErr(r.error); if (r.items && r.items.length) setNewsList(r.items); }
  };
  // auto-fetch once on first open of the 消息 tab (cache hit = fast; miss = FinMind)
  useEffect(() => { if (tab === 'news' && code && newsList.length === 0 && !newsBusy) fetchNews(false); }, [tab]); // eslint-disable-line


  const mine = rows.filter(r => r.code === code);
  const latest = mine[mine.length - 1] || null;
  const lastBar = doc && doc.daily && doc.daily.length ? doc.daily[doc.daily.length - 1] : null;

  const TABS = [
    { k: 'predict', l: '预测' },
    { k: 'env', l: '环境' },
    { k: 'news', l: '消息' },
    { k: 'review', l: '复盘' },
    { k: 'ai', l: 'AI点评' },
    { k: 'memory', l: '记忆' },
  ];

  return (
    <div className="sidebar">
      <div className="tabs">
        {TABS.map(t => (
          <button key={t.k} className={'tabbtn' + (tab === t.k ? ' active' : '')} onClick={() => setTab(t.k)}>{t.l}</button>
        ))}
      </div>
      <div className="tabbody" ref={bodyRef}>
        {tab === 'predict' && (
          <div className="kv">
            {!latest && <div className="muted">尚無凍結點評（跑 etl/cockpit_p2.py {code}，或到 AI点评 按「再評一次」）</div>}
            {latest && (
              <>
                <div className="kvrow"><span>as_of</span><b>{latest.as_of}</b></div>
                {latest.scenarios && (
                  <>
                    <div className="kvrow"><span>看多</span><b className="up">{n2(latest.scenarios.bull)}</b></div>
                    <div className="kvrow"><span>基準</span><b>{n2(latest.scenarios.base)}</b></div>
                    <div className="kvrow"><span>看空</span><b className="dn">{n2(latest.scenarios.bear)}</b></div>
                  </>
                )}
                {latest.fields && Object.keys(latest.fields).slice(0, 14).map(k => (
                  <div className="kvrow" key={k}><span>{k}</span><b>{String(latest.fields[k])}</b></div>
                ))}
                {latest.hit_rate != null && <div className="kvrow"><span>命中率</span><b>{latest.hit_rate}</b></div>}
              </>
            )}
            {lastBar && <div className="kvrow"><span>最新收</span><b>{n2(lastBar.close)} <i className="muted">({lastBar.time})</i></b></div>}
          </div>
        )}
        {tab === 'env' && (
          <div className="kv">
            <div className="muted" style={{ margin: '4px 0 8px' }}>環境（FundFlo T−1 + 基準 ETF + 市況）</div>
            {fundRow ? (
              <>
                <div className="kvrow"><span>外資 5 日</span><b className={fundRow.foreign_flow_yi >= 0 ? 'up' : 'dn'}>{n2(fundRow.foreign_flow_yi)} 億</b></div>
                <div className="kvrow"><span>加總 5 日</span><b className={(fundRow.combined_flow_yi ?? 0) >= 0 ? 'up' : 'dn'}>{n2(fundRow.combined_flow_yi)} 億</b></div>
                {fundRow.rolling_ret_5d != null && <div className="kvrow"><span>5 日漲跌</span><b className={(fundRow.rolling_ret_5d >= 0 ? 'up' : 'dn')}>{(fundRow.rolling_ret_5d >= 0 ? '+' : '') + fundRow.rolling_ret_5d.toFixed(2)}%</b></div>}
              </>
            ) : <div className="muted">未收錄於 FundFlo（不在追蹤清單）</div>}
            {etf && (
              <>
                <div className="kvrow"><span>00981A</span><b>{etf.name || '金融ETF'} <i className="muted">{etf.date || ''}</i></b></div>
                {etf.meta?.n_equity != null && <div className="kvrow"><span>持股</span><b>{etf.meta.n_equity} 檔（{etf.meta.weight_sum_equity}%）</b></div>}
              </>
            )}
            {regime && (
              <>
                <div className="kvrow"><span>市況</span><b>{regime.primary_label || regime.regime || '—'}</b></div>
                {regime.secondary_label && <div className="kvrow"><span>次</span><b>{regime.secondary_label}</b></div>}
                {regime.confidence != null && <div className="kvrow"><span>信心</span><b>{regime.confidence}</b></div>}
              </>
            )}
            {overlay && (
              <div className="kvrow"><span>量比</span><b>{n2(overlay.vol_ratio)}</b></div>
            )}
          </div>
        )}
        {tab === 'memory' && (
          <SymbolMemory code={code} />
        )}
        {tab === 'news' && (
          <div className="kv">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
              <span className="muted">新聞（FinMind 日股新聞）</span>
              <button className="btn" onClick={fetchNews} disabled={newsBusy}>{newsBusy ? '抓取中…' : '抓取'}</button>
            </div>
            {newsErr && <div className="muted" style={{ marginBottom: 6 }}>{newsErr}</div>}
            {newsList.length === 0 && <div className="muted">尚無新聞（點「抓取」從 FinMind 拉取 {code}）</div>}
            {newsList.slice(0, 20).map((n, i) => (
              <div key={i} className="news">
                <div className="muted">{n.time || n.date || ''}</div>
                <div>{n.url ? <a href={n.url} target="_blank" rel="noreferrer">{n.title}</a> : n.title}</div>
              </div>
            ))}
          </div>
        )}
        {tab === 'review' && (
          <ReviewTab code={code} rows={rows} />
        )}
        {tab === 'ai' && (
          <AiFeed code={code} latest={latest} onP2={onP2} p2stat={p2stat} />
        )}
      </div>

      {/* ChatDock — 及時 AI 協助 (kansoku ChatDock: docked under the sidebar) */}
      <div className="chatdock">
        <ChatDock code={code} overlay={overlay} onAsk={onAsk} busy={askBusy} />
      </div>
    </div>
  );
}

// ---------- 復盤 (kansoku ReviewTab port: 历史 | 日志 | 笔记) ----------
const OUTCOME_LABEL = {
  hit_target: { t: '到目標', tone: 'up' },
  hit_stop: { t: '到止損', tone: 'dn' },
  held_range: { t: '守住區間', tone: 'up' },
  broke_range: { t: '破區間', tone: 'dn' },
  open: { t: '進行中', tone: '' },
};
const DIR_LABEL = { long: '多', short: '空', neutral: '觀望' };

function ReviewTab({ code, rows }) {
  const [sub, setSub] = useState('history');
  const [hist, setHist] = useState(null);
  const [journal, setJournal] = useState(null); // {dates, rows}
  const [selDate, setSelDate] = useState(null);
  const [note, setNote] = useState(() => noteGet(code));

  const reload = async () => {
    setHist(await historyRows(code));
    const d = await comments(code, selDate);
    setJournal(d && d.feed ? d : null);
  };
  useEffect(() => {
    setSub('history'); setSelDate(null); setNote(noteGet(code)); setHist(null); setJournal(null);
    reload();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code]);
  useEffect(() => { if (sub === 'journal') reload(); }, [sub]); // eslint-disable-line

  const hitRate = (rows_) => {
    const scored = rows_.filter(r => r.outcome && r.outcome.status !== 'open');
    if (!scored.length) return null;
    const good = scored.filter(r => ['hit_target', 'held_range'].includes(r.outcome.status)).length;
    return good / scored.length;
  };

  return (
    <div className="kv">
      <div className="subtabs">
        {[['history', '历史'], ['journal', '日志'], ['note', '笔记']].map(([k, l]) => (
          <button key={k} className={'subtab' + (sub === k ? ' active' : '')} onClick={() => setSub(k)}>{l}</button>
        ))}
      </div>

      {sub === 'history' && (
        <div>
          {hist === null && <div className="muted">載入中…</div>}
          {hist && !hist.length && <div className="muted">尚無凍結記錄</div>}
          {hist && hist.length > 0 && (
            <>
              {hitRate(hist) != null && (
                <div className="kvrow"><span>命中率（已結算）</span><b>{(hitRate(hist) * 100).toFixed(0)}%</b></div>
              )}
              {hist.map((r, i) => {
                const o = r.outcome || {};
                const oc = OUTCOME_LABEL[o.status] || OUTCOME_LABEL.open;
                return (
                  <div key={i} className={'hrow dir-' + (o.direction || 'neutral')}>
                    <div className="hhead">
                      <b>{r.as_of}</b>
                      <span className="muted">{DIR_LABEL[o.direction] || '—'}</span>
                    </div>
                    <div className="hmeta">
                      錨 {n2(o.anchor)}
                      {o.last != null && <> · 現 {n2(o.last)}</>}
                      {o.pct != null && <span className={o.pct >= 0 ? 'up' : 'dn'}>{o.pct >= 0 ? '+' : ''}{o.pct}%</span>}
                    </div>
                    <span className={'houtcome ' + oc.tone}>{oc.t}</span>
                    {r.scenarios && <div className="hmeta muted">多 {n2(r.scenarios.bull)} · 基 {n2(r.scenarios.base)} · 空 {n2(r.scenarios.bear)}</div>}
                  </div>
                );
              })}
            </>
          )}
        </div>
      )}

      {sub === 'journal' && (
        <div>
          {journal === null && <div className="muted">載入中…</div>}
          {journal && (journal.dates || []).length > 0 && (
            <select className="date-sel" value={selDate || 'today'}
              onChange={e => setSelDate(e.target.value === 'today' ? null : e.target.value)}>
              <option value="today">今天</option>
              {journal.dates.map(d => <option key={d} value={d}>{d}</option>)}
            </select>
          )}
          {journal && (journal.feed || []).length === 0 && <div className="muted">該日無點評（盘面上触发时 AI 会写入日志）</div>}
          {journal && (journal.feed || []).slice().reverse().map((row, i) => {
            const c = row.kind === 'comment' ? row.comment : row.comments[0];
            return (
              <div key={i} className="jentry">
                <div className="muted">{c ? new Date(Number(c.ts) * 1000).toLocaleString('zh-TW', { timeZone: 'Asia/Taipei', hour12: false }) : ''}</div>
                {c && <div>{(c.text || '').slice(0, 80)}</div>}
              </div>
            );
          })}
        </div>
      )}

      {sub === 'note' && (
        <div>
          <textarea className="note-area" rows={8} placeholder={`記 ${code} 的復盤筆記…`}
            value={note} onChange={e => setNote(e.target.value)}
            onBlur={() => noteSet(code, note)} />
          <div className="muted" style={{ fontSize: 10.5, marginTop: 4 }}>自動存本地（localStorage），{note ? '已存' : '未存'}</div>
        </div>
      )}
    </div>
  );
}

// ---------- AI點評 feed (kansoku AiTab + aiFeed + AnalysisRunDetails port) ----------
const PHASE_LABEL = { preparing: '準備環境', researching: '收集資料', writing: '寫入復盤', finalizing: '生成結論' };
const ORIGIN_LABEL = { manual: '手動分析', escalation: '自動升級分析' };
const LEVEL_TONE = { info: '', warn: 'accent', alert: 'dn' };
const SOURCE_LABEL = { analyst: '分析員', system: '系統', commentator: '', explainer: '' };

function fmtClock(ts) {
  if (!ts) return '';
  const d = new Date(Number(ts));
  if (Number.isNaN(d.getTime())) return String(ts).slice(11, 16);
  return d.toLocaleTimeString('zh-TW', { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit', timeZone: 'Asia/Taipei' });
}
function fmtElapsed(ms) {
  const s = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(s / 60), h = Math.floor(m / 60);
  if (h > 0) return `${h} 小時 ${String(m % 60).padStart(2, '0')} 分`;
  if (m > 0) return `${m} 分 ${String(s % 60).padStart(2, '0')} 秒`;
  return `${s} 秒`;
}

function CommentEntry({ c }) {
  const dim = c.source === 'commentator' && c.level === 'info';
  return (
    <div className={'ai-item' + (dim ? ' dim' : '')}>
      <div className="ai-meta-row">
        <span className="t">{fmtClock(c.ts)}</span>
        {c.level && <span className={'badge' + (LEVEL_TONE[c.level] ? ' ' + LEVEL_TONE[c.level] : '')}>{c.level}</span>}
        {c.stance && <span className={'badge' + ' ' + (STANCE_TONE[c.stance] || '')}>{STANCE_LABEL[c.stance]}</span>}
      </div>
      <p className="ai-fact">{c.text}</p>
      {c.read && <p className="ai-read">{c.read}</p>}
      {c.stance_note && <p className={'ai-stance' + (dim ? ' muted' : '')}>{c.stance_note}</p>}
      {c.source === 'explainer' && c.text && <div className="ai-explainer-card" dangerouslySetInnerHTML={{ __html: mdToHtml(c.text) }} />}
      {((c.trigger || (SOURCE_LABEL[c.source] && c.source !== 'commentator')) && (
        <div className="ai-meta">
          {c.trigger && <span>觸發：{c.trigger}</span>}
          {c.trigger && SOURCE_LABEL[c.source] && <span className="sep"> · </span>}
          {SOURCE_LABEL[c.source] && c.source !== 'commentator' && <span>{SOURCE_LABEL[c.source]}</span>}
        </div>
      ))}
    </div>
  );
}

function ReassessPanel({ status, now }) {
  if (!status) return null;
  const started = Number(status.started_at || 0) * 1000;
  const elapsed = started ? fmtElapsed(now - started) : '時間未知';
  return (
    <div className="ai-run-status">
      <span className="dot pulse" aria-hidden="true" />
      <div>
        <div className="head">
          <b>{PHASE_LABEL[status.phase] || status.phase}</b>
          <span className="muted">{ORIGIN_LABEL[status.origin] || '手動分析'} · 已運行 {elapsed}</span>
        </div>
        <div className="activity">{status.activity}</div>
        <div className="meta muted">開始於 {status.started_at ? new Date(status.started_at * 1000).toLocaleString('zh-TW', { timeZone: 'Asia/Taipei', hour12: false }) : '—'}</div>
      </div>
    </div>
  );
}

function AiFeed({ code, latest, onP2, p2stat }) {
  const [data, setData] = useState(null);
  const [selDate, setSelDate] = useState(null);
  const [expanded, setExpanded] = useState({});
  const [run, setRun] = useState(null);      // running reassess status
  const [hint, setHint] = useState(null);
  const [explaining, setExplaining] = useState(false);
  const [now, setNow] = useState(Date.now());
  const codeRef = useRef(code);

  const reload = async (d) => {
    const c = await comments(codeRef.current, d || undefined);
    if (c && c.feed) setData(c);
  };

  // load on code change / mount
  useEffect(() => {
    codeRef.current = code;
    setSelDate(null); setRun(null); setHint(null); setData(null);
    reload(code);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [code]);
  // poll feed every 20s
  useEffect(() => {
    const t = setInterval(() => reload(selDate), 20000);
    return () => clearInterval(t);
  }, [code, selDate]);
  // poll reassess status while running
  useEffect(() => {
    if (!run) return;
    const t = setInterval(async () => {
      setNow(Date.now());
      const s = await reassessStatus(code);
      const st = s && s.status;
      if (!st || !st.running) {
        setRun(null);
        setHint(st && st.activity ? `完成：${st.activity}` : null);
        setTimeout(() => setHint(null), 8000);
        reload(selDate);
      } else {
        setRun(st);
      }
    }, 2000);
    return () => clearInterval(t);
  }, [run, code]);

  const start = async () => {
    setHint(null);
    const r = await reassessStart(code, 'manual');
    if (r.error) { setHint(r.error); return; }
    if (r.reason === 'already-running') { setHint('已有分析在跑'); return; }
    if (r.started) setRun({ running: true, origin: 'manual', phase: 'preparing', activity: '正在等待服務端確認任務' });
    else setHint(r.reason || '未能啟動分析');
  };
  const doExplain = async () => {
    setExplaining(true);
    const r = await explain(code);
    setExplaining(false);
    if (r.ok) reload(selDate);
    else if (r.error) setHint(r.error);
  };

  const dates = (data && data.dates) || [];
  const today = new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Taipei' });
  const pastDates = dates.filter(d => d < today);
  const feed = (data && data.feed) || [];
  const rows = selDate ? feed.slice().reverse() : feed.slice().reverse();

  return (
    <div className="kv">
      <div className="ai-toolbar">
        <button className="btn primary" onClick={start} disabled={!!run}>{run ? '重估進行中…' : '重新分析'}</button>
        <button className="btn" onClick={doExplain} disabled={explaining || !latest}>{explaining ? '解釋中…' : '解釋此分析'}</button>
        {pastDates.length > 0 && (
          <select className="date-sel" value={selDate || 'today'} onChange={(e) => setSelDate(e.target.value === 'today' ? null : e.target.value)}>
            <option value="today">今天</option>
            {pastDates.map(d => <option key={d} value={d}>{d}</option>)}
          </select>
        )}
      </div>
      {hint && <div className="muted hint">{hint}</div>}
      {selDate && <div className="muted note">顯示 {selDate} 的點評（今天暫無新點評）</div>}
      {run && <ReassessPanel status={run} now={now} />}
      {p2stat && <div className="muted hint">凍結點評：{p2stat}</div>}
      {!rows.length && !run && (
        <div className="muted">
          暫無點評。盤面出現觸發事件時，AI 會在這裏給出研判；也可以點上面「重新分析」手動跑一次重估
        </div>
      )}
      <div className="feed">
        {rows.map(row => {
          if (row.kind === 'fold') {
            const open = !!expanded[row.id];
            return (
              <div key={row.id}>
                <div className="fold" onClick={() => setExpanded(x => ({ ...x, [row.id]: !open }))}>
                  {fmtClock(row.from)} – {fmtClock(row.to)} 無事 ×{row.count}（{open ? '收起' : '點擊展開'}）
                </div>
                {open && row.comments.map(c => <CommentEntry key={`${c.ts}-${c.text}`} c={c} />)}
              </div>
            );
          }
          return <CommentEntry key={row.comment.ts + '-' + row.comment.text} c={row.comment} />;
        })}
      </div>
    </div>
  );
}

function ChatDock({ code, overlay, onAsk, busy }) {
  const [msgs, setMsgs] = useState([]);
  const [q, setQ] = useState('');
  const boxRef = useRef(null);
  useEffect(() => { if (boxRef.current) boxRef.current.scrollTop = boxRef.current.scrollHeight; }, [msgs]);

  const quick = (text) => {
    setMsgs(m => [...m, { w: 'u', t: text }]);
    onAsk(text).then(ans => setMsgs(m => [...m, { w: 'a', t: ans }]));
  };

  return (
    <div>
      <div className="chathead">及時 AI · {code} <span className="muted">（讀當前 K+疊加+法人）</span></div>
      <div className="msgs" ref={boxRef}>
        {!msgs.length && <div className="muted">例：現在量比多少？</div>}
        {msgs.map((m, i) => <div key={i} className={'m ' + m.w}>{m.t}</div>)}
        {busy && <div className="m a muted">LLM 運算中…</div>}
      </div>
      <div className="qchips">
        <button className="btn" disabled={busy} onClick={() => quick('现在量比多少？')}>量比</button>
        <button className="btn" disabled={busy} onClick={() => quick('MA20 和 RSI 現在誰比較弱？')}>MA20/RSI</button>
        <button className="btn" disabled={busy} onClick={() => quick('外資最近在買還是賣？')}>法人</button>
      </div>
      <div className="cin">
        <input value={q} placeholder="問…" disabled={busy}
          onChange={e => setQ(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter' && q.trim()) { const t = q; setQ(''); quick(t); } }} />
        <button className="btn primary" disabled={busy || !q.trim()} onClick={() => { const t = q; setQ(''); quick(t); }}>問</button>
      </div>
    </div>
  );
}
