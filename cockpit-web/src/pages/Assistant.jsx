import { useEffect, useRef, useState } from 'react';
import { helperAsk } from '../lib/data.js';

// /assistant — light port of kansoku assistant/ (session list + conversation).
// Sessions persisted in localStorage (no keys, head vLLM via :8790 /ask).
const LS = 'kdw:assistant:sessions';

function loadSessions() {
  try { return JSON.parse(localStorage.getItem(LS) || '[]'); } catch (_) { return []; }
}
function saveSessions(s) { localStorage.setItem(LS, JSON.stringify(s.slice(-30))); }

export default function Assistant() {
  const [sessions, setSessions] = useState(() => {
    const s = loadSessions();
    return s.length ? s : [{ id: String(Date.now()), title: '新對話', msgs: [] }];
  });
  const [cur, setCur] = useState(0);
  const [q, setQ] = useState('');
  const [busy, setBusy] = useState(false);
  const boxRef = useRef(null);
  const s = sessions[cur];

  useEffect(() => { if (boxRef.current) boxRef.current.scrollTop = boxRef.current.scrollHeight; }, [s?.msgs, busy]);

  const newSession = () => {
    const ns = [...sessions, { id: String(Date.now()), title: '新對話', msgs: [] }];
    setSessions(ns); setCur(ns.length - 1); saveSessions(ns);
  };
  const pick = (i) => setCur(i);

  const send = async () => {
    if (!q.trim() || busy) return;
    const question = q; setQ('');
    let s0 = sessions[cur];
    if (!s0) { newSession(); return; }
    const withUser = { ...s0, msgs: [...s0.msgs, { w: 'u', t: question }] };
    const upd = (idx, obj) => { const ns = sessions.map((x, i) => (i === idx ? obj : x)); setSessions(ns); saveSessions(ns); };
    upd(cur, { ...withUser, title: s0.msgs.length ? s0.title : question.slice(0, 24) });
    setBusy(true);
    const ctx = s0.msgs.slice(-8).map(m => (m.w === 'a' ? `助手: ${m.t}` : `用戶: ${m.t}`)).join('\n');
    const out = await helperAsk('ASSIST', question + (ctx ? `\n（前文：${ctx.slice(-800)}）` : ''), { tf: 'assistant', overlays: {}, fundflo: {}, bars: [], doc_excerpt: '' });
    const ans = out.ok ? out.answer : (out.error || 'LLM 離線');
    const done = { ...withUser, msgs: [...withUser.msgs, { w: 'a', t: ans }] };
    const idx = sessions.findIndex(x => x.id === s0.id);
    upd(idx >= 0 ? idx : cur, done);
    setBusy(false);
  };

  const remove = (i) => {
    const ns = sessions.filter((_, j) => j !== i);
    const final = ns.length ? ns : [{ id: String(Date.now()), title: '新對話', msgs: [] }];
    setSessions(final); setCur(0); saveSessions(final);
  };

  return (
    <div className="page assistant">
      <div className="topstrip">
        <div>
          <div className="hs">AI 助理</div>
          <div className="muted">本地 vLLM（head · qwen3.8-flash-next）· 對話存本地</div>
        </div>
        <button className="btn" onClick={newSession}>+ 新對話</button>
      </div>
      <div className="ass-grid">
        <div className="card ass-sess">
          <div className="jlist">
            {sessions.map((x, i) => (
              <div key={x.id} className={'jrow' + (i === cur ? ' active' : '')} onClick={() => pick(i)}>
                <span className="jd" style={{ flex: 1 }}>{x.title}</span>
                <button className="jdel" title="刪除" onClick={(e) => { e.stopPropagation(); remove(i); }}>×</button>
              </div>
            ))}
          </div>
        </div>
        <div className="card ass-main">
          <div className="msgs" ref={boxRef}>
            {(!s || !s.msgs.length) && <div className="muted">問任何台股問題，例：「現在盤面哪些訊號值得注意？」</div>}
            {(s?.msgs || []).map((m, i) => <div key={i} className={'m ' + m.w}>{m.t}</div>)}
            {busy && <div className="m a muted">LLM 運算中…</div>}
          </div>
          <div className="cin">
            <input value={q} placeholder="問…" disabled={busy}
              onChange={e => setQ(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') send(); }} />
            <button className="btn primary" disabled={busy || !q.trim()} onClick={send}>問</button>
          </div>
        </div>
      </div>
    </div>
  );
}
