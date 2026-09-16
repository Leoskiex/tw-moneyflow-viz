import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  jget, jraw, DATA, getJsonl, helperAsk, mdToHtml, researchDraft, researchSave,
} from '../lib/data.js';

// /research — 研究庫 three-pane inside the shell (left list | center doc | right 追問)
// #17: AI 起草（head vLLM）→ 可編輯 → 存回 data/research/{code}.md
export default function Research() {
  const [items, setItems] = useState([]);
  const [cur, setCur] = useState(null);
  const [docText, setDocText] = useState('');
  const [editing, setEditing] = useState(false);
  const [draftBusy, setDraftBusy] = useState(false);
  const [saveBusy, setSaveBusy] = useState(false);
  const [savedNote, setSavedNote] = useState('');
  const [askBusy, setAskBusy] = useState(false);
  const [msgs, setMsgs] = useState([]);
  const [q, setQ] = useState('');

  const refresh = async () => {
    const jsonl = await getJsonl();
    const codes = new Set(jsonl.map(r => r.code).filter(Boolean));
    for (const c of ['2454', '2330', '2317']) codes.add(c);
    const out = [];
    await Promise.all([...codes].map(async (code) => {
      const txt = await jraw(DATA(`data/research/${code}.md`));
      if (!txt) return;
      const asof = (txt.match(/as_of[=（:]\s*([0-9-]{8,10})/) || [])[1] || '';
      out.push({ code, asof, text: txt });
    }));
    for (const r of jsonl) {
      const ex = out.find(o => o.code === r.code);
      if (ex) { if (r.as_of && (!ex.asof || r.as_of > ex.asof)) ex.asof = r.as_of; }
      else out.push({ code: r.code, asof: r.as_of || '', text: '', row: r });
    }
    out.sort((a, b) => (b.asof || '').localeCompare(a.asof || ''));
    setItems(out);
    return out;
  };

  useEffect(() => { (async () => { const out = await refresh(); if (!cur && out.length) { setCur(out[0].code); setDocText(out[0].text || ''); } })(); }, []); // eslint-disable-line

  const pick = (o) => { setCur(o.code); setDocText(o.text || ''); setMsgs([]); setEditing(false); setSavedNote(''); };

  const ask = async () => {
    if (!q.trim() || !cur) return;
    const question = q; setQ(''); setAskBusy(true);
    setMsgs(m => [...m, { w: 'u', t: question }]);
    const out = await helperAsk(cur, question, { tf: '研究庫', overlays: {}, fundflo: {}, bars: [], doc_excerpt: (docText || '').slice(0, 3000) });
    setMsgs(m => [...m, { w: 'a', t: out.ok ? out.answer : (out.error || 'LLM 離線') }]);
    setAskBusy(false);
  };

  const draft = async () => {
    if (!cur) return;
    setDraftBusy(true); setSavedNote('');
    const r = await researchDraft(cur);
    setDraftBusy(false);
    if (r.ok) { setDocText(r.markdown || ''); setEditing(true); setSavedNote('AI 起草完成 — 可編輯後保存'); }
    else setSavedNote(r.error || '起草失敗');
  };

  const save = async () => {
    if (!cur || !docText.trim()) return;
    setSaveBusy(true);
    const r = await researchSave(cur, docText);
    setSaveBusy(false); setEditing(false);
    if (r.ok) { setSavedNote(`已存 data/research/${cur}.md（${r.size}B）`); await refresh(); }
    else setSavedNote(r.error || '保存失敗');
  };

  return (
    <div className="research">
      <div className="r-left">
        <div className="card" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          <h3>研究檔 · 凍結點評</h3>
          <div className="jlist">
            {items.length === 0 && <div className="muted" style={{ padding: 10 }}>尚無研究檔 — 到個股頁按「再評一次」生成。</div>}
            {items.map((o, i) => (
              <div key={i} className={'jrow' + (cur === o.code ? ' active' : '')} onClick={() => pick(o)}>
                <span className="jc">{o.code}</span>
                <span className="jd muted">{o.asof || '無 md'}</span>
                <span className="jtag">{o.text ? 'md' : 'jsonl'}</span>
                <Link to={`/symbol/${o.code}`} style={{ fontSize: 11 }} onClick={e => e.stopPropagation()}>K線</Link>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="r-center">
        <div className="card" style={{ height: '100%' }}>
          <div className="rc-toolbar">
            <button className="btn primary" onClick={draft} disabled={draftBusy || !cur}>{draftBusy ? '起草中…（LLM 讀 30 日 K+法人+凍結點評）' : 'AI 起草'}</button>
            <button className="btn" onClick={() => setEditing(e => !e)} disabled={!cur}>
              {editing ? '完成編輯' : '編輯'}
            </button>
            <button className="btn" onClick={save} disabled={saveBusy || !editing || !docText.trim()}>
              {saveBusy ? '保存中…' : `存 ${cur || ''}.md`}
            </button>
            {savedNote && <span className="muted" style={{ fontSize: 11 }}>{savedNote}</span>}
          </div>
          {editing ? (
            <textarea className="md-edit" value={docText} onChange={e => setDocText(e.target.value)}
              placeholder="研究檔 markdown（AI 起草或自填）" style={{ height: 'calc(100% - 44px)', marginTop: 8 }} />
          ) : docText ? (
            <div className="md" dangerouslySetInnerHTML={{ __html: mdToHtml(docText) }} />
          ) : (
            <div className="muted" style={{ padding: 14 }}>← 選左側研究檔，或按「AI 起草」</div>
          )}
        </div>
      </div>
      <div className="r-right">
        <div className="card" style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
          <h3>追問（本機 LLM）</h3>
          <div className="msgs">
            {msgs.length === 0 && <div className="muted">對這份研究檔追問，例：「ma20 和 rsi14 現在誰比較弱？」</div>}
            {msgs.map((m, i) => <div key={i} className={'m ' + m.w}>{m.t}</div>)}
            {askBusy && <div className="m a muted">LLM 運算中…</div>}
          </div>
          <div className="cin">
            <input value={q} placeholder="追問…" disabled={askBusy}
              onChange={e => setQ(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') ask(); }} />
            <button className="btn primary" disabled={askBusy || !q.trim()} onClick={ask}>問</button>
          </div>
        </div>
      </div>
    </div>
  );
}
