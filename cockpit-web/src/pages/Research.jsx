import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  HELPER, jget, jraw, DATA, getJsonl, helperAsk, mdToHtml, researchDraft, researchSave,
  researchDeepStart, researchDeepStatus, researchRead,
} from '../lib/data.js';
// /research — 研究庫 three-pane inside the shell (left list | center doc | right 追問)
// #17: AI 起草（head vLLM）→ 可編輯 → 存回 data/research/{code}.md
// WAVE 3 P2: 深度研究（:8790 /research-deep）→ data/research/{code}-deep-YYYYMMDD.md + 進度 UI
const DEEP_PHASES = ['queued', 'pack', 'llm', 'write'];
const DEEP_LABEL = { queued: '排隊', pack: '打包資料', llm: 'LLM 寫六節', write: '寫入', done: '完成', error: '失敗' };

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
  const [deep, setDeep] = useState(null); // deep-research job status for cur
  const [deepDocs, setDeepDocs] = useState([]); // {code, name, asof, mtime}
  const [curDeep, setCurDeep] = useState(false); // viewing the deep md for cur
  const [deepBusy, setDeepBusy] = useState(false);
  const pollRef = useRef(null);

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
    // WAVE 3 P2: deep docs from helper /research (flagged {code}-deep-*.md)
    const dd = await jget(HELPER ? `${HELPER}/research` : null);
    const deepList = ((dd && dd.docs) || []).filter(d => d.deep).map(d => ({
      code: d.code, name: d.name, asof: (d.stem.match(/deep-(\d{8})/) || [])[1] || '', mtime: d.mtime,
    }));
    deepList.sort((a, b) => (b.asof || '').localeCompare(a.asof || '') || (b.mtime - a.mtime));
    setDeepDocs(deepList);
    return out;
  };

  useEffect(() => {
    (async () => { const out = await refresh(); if (!cur && out.length) { setCur(out[0].code); setDocText(out[0].text || ''); } })();
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []); // eslint-disable-line

  const pick = (o) => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }
    setCur(o.code); setCurDeep(false); setDocText(o.text || ''); setMsgs([]); setEditing(false); setSavedNote(''); setDeep(null);
  };
  const pickDeep = async (code) => {
    setCur(code); setCurDeep(true); setMsgs([]); setEditing(false); setSavedNote('');
    const r = await researchRead(code, true);
    setDocText((r && r.text) || '');
  };

  // WAVE 3 P2: start deep research + poll phase file until done/error
  const deepStart = async () => {
    if (!cur || deepBusy) return;
    setDeepBusy(true); setSavedNote('');
    const st = await researchDeepStart(cur);
    if (st.error) { setSavedNote(st.error); setDeepBusy(false); return; }
    if (!st.started && st.reason === 'already-running') setSavedNote('已有深度研究在跑');
    pollRef.current = setInterval(async () => {
      const s = await researchDeepStatus(cur);
      const j = s && s.status;
      if (!j) return;
      setDeep(j);
      if (!j.running) {
        clearInterval(pollRef.current); pollRef.current = null; setDeepBusy(false);
        if (j.phase === 'done') {
          const r = await researchRead(cur, true);
          setDocText((r && r.text) || ''); setCurDeep(true); setEditing(false);
          setSavedNote(`深度研究完成 — ${r ? r.name : 'md'}`);
          await refresh();
        } else {
          setSavedNote(j.activity || '失敗（未產出假檔）');
        }
      }
    }, 2000);
  };

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
              <div key={'f' + i} className={'jrow' + (cur === o.code && !curDeep ? ' active' : '')} onClick={() => pick(o)}>
                <span className="jc">{o.code}</span>
                <span className="jd muted">{o.asof || '無 md'}</span>
                <span className="jtag">{o.text ? 'md' : 'jsonl'}</span>
                <Link to={`/symbol/${o.code}`} style={{ fontSize: 11 }} onClick={e => e.stopPropagation()}>K線</Link>
              </div>
            ))}
            {deepDocs.length > 0 && <div className="muted" style={{ padding: '8px 10px 2px', fontSize: 11 }}>深度研究（六節）</div>}
            {deepDocs.map((o, i) => (
              <div key={'d' + i} className={'jrow jdeep' + (cur === o.code && curDeep ? ' active' : '')} onClick={() => pickDeep(o.code)}>
                <span className="jc">{o.code}</span>
                <span className="jd muted">{o.asof ? o.asof.replace(/(\d{4})(\d{2})(\d{2})/, '$1-$2-$3') : 'deep'}</span>
                <span className="jtag">深度</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="r-center">
        <div className="card" style={{ height: '100%' }}>
          <div className="rc-toolbar">
            <button className="btn primary" onClick={deepStart} disabled={deepBusy || !cur}>
              {deepBusy ? '深度研究中…' : '深度研究'}
            </button>
            <button className="btn primary" onClick={draft} disabled={draftBusy || !cur || curDeep}>{draftBusy ? '起草中…（LLM 讀 30 日 K+法人+凍結點評）' : 'AI 起草'}</button>
            <button className="btn" onClick={() => setEditing(e => !e)} disabled={!cur || curDeep}>
              {editing ? '完成編輯' : '編輯'}
            </button>
            <button className="btn" onClick={save} disabled={saveBusy || !editing || !docText.trim() || curDeep}>
              {saveBusy ? '保存中…' : `存 ${cur || ''}.md`}
            </button>
            {curDeep && <span className="pill" style={{ fontSize: 11 }}>深度研究檔（唯讀）</span>}
            {savedNote && <span className="muted" style={{ fontSize: 11 }}>{savedNote}</span>}
          </div>
          {deepBusy && deep && (
            <div className="deep-progress">
              <div className="deep-phases">
                {DEEP_PHASES.map((ph, i) => {
                  const curIdx = DEEP_PHASES.indexOf(deep.phase);
                  const on = curIdx >= 0 ? i <= curIdx : i === 0;
                  return <span key={ph} className={'deep-ph' + (on ? ' on' : '')}>{DEEP_LABEL[ph]}</span>;
                })}
              </div>
              <div className="muted" style={{ fontSize: 11 }}>{deep.activity || '…'}</div>
            </div>
          )}
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
