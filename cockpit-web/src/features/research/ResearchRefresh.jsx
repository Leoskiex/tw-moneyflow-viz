import { useEffect, useRef, useState } from 'react';
import {
  mdToHtml, researchRefreshStart, researchRefreshStatus,
  researchProposals, researchAdopt, researchTimeline,
} from '../../lib/data.js';

// WAVE 4 D4 P3 — 研究庫刷新採納 (self-built; kansoku §3 inferred, not copied).
// Flow: 「刷新提案」→ :8790/research-refresh (re-write + proposal + diff) → poll →
//       show diff summary + proposed md → 採納 (backup→history, overwrite, timeline) / 拒絕 (md unchanged).
// LLM down → clear error; no fake proposal.
const PHASES = ['queued', 'pack', 'llm', 'write'];
const P_LABEL = { queued: '排隊', pack: '打包+讀舊檔', llm: 'LLM 重刷', write: '寫提案+diff', done: '完成', error: '失敗' };

const STATUS_TXT = { open: '待處理', adopted: '已採納', rejected: '已拒絕' };

export default function ResearchRefresh({ code, onAdopted }) {
  const [job, setJob] = useState(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState('');
  const [proposals, setProposals] = useState([]);
  const [detail, setDetail] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [acting, setActing] = useState(false);
  const pollRef = useRef(null);

  const load = async () => {
    if (!code) return;
    const p = await researchProposals(code);
    setProposals(p.proposals || []);
    const t = await researchTimeline(code);
    setTimeline(t.rows || []);
    // if an open proposal exists and none selected, auto-select the newest open
    if (!detail && p.proposals.length) {
      const open = (p.proposals || [])[0];
      if (open) await select(open.file);
    }
  };
  const select = async (file) => {
    const p = await researchProposals(code, file);
    setDetail(p.detail || null);
  };

  useEffect(() => {
    setDetail(null); setJob(null); setNote('');
    load();
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [code]); // eslint-disable-line

  const start = async () => {
    if (!code || busy) return;
    setBusy(true); setNote(''); setDetail(null);
    const st = await researchRefreshStart(code, '');
    if (st.error) { setNote(st.error); setBusy(false); return; }
    if (st.started === false && st.reason === 'already-running') setNote('已有刷新在跑');
    pollRef.current = setInterval(async () => {
      const s = await researchRefreshStatus(code);
      const j = s && s.status;
      if (!j) return;
      setJob(j);
      if (!j.running) {
        clearInterval(pollRef.current); pollRef.current = null; setBusy(false);
        if (j.phase === 'done') {
          await load();
          setNote('刷新完成 — 可採納或拒絕');
        } else {
          setNote(j.activity || '失敗（未產出假提案）');
        }
      }
    }, 2000);
  };

  const act = async (action) => {
    if (!detail || !detail.file || acting) return;
    setActing(true); setNote('');
    const r = await researchAdopt(code, detail.file, action);
    setActing(false);
    if (r.ok) {
      if (action === 'adopt') {
        setNote(`已採納 ${detail.file} → ${r.target}（備份 ${r.backup}）`);
        setDetail(null);
        await load();
        if (onAdopted) onAdopted();
      } else {
        setNote(`已拒絕 ${detail.file}（md 不變）`);
        setDetail(null);
        await load();
      }
    } else {
      setNote(r.error || '操作失敗');
    }
  };

  const diff = detail && detail.diff;
  const sec = (diff && diff.sections) || {};
  const diffLines = (diff && diff.diff_lines) || [];

  return (
    <div className="refresh">
      <div className="rf-top">
        <button className="btn primary" onClick={start} disabled={busy}>
          {busy ? '刷新中…' : '刷新提案'}
        </button>
        {note && <span className="muted" style={{ fontSize: 11 }}>{note}</span>}
      </div>

      {busy && job && (
        <div className="deep-progress">
          <div className="deep-phases">
            {PHASES.map((ph, i) => {
              const idx = PHASES.indexOf(job.phase);
              return <span key={ph} className={'deep-ph' + (idx >= 0 ? (i <= idx ? ' on' : '') : ' on')}>{P_LABEL[ph]}</span>;
            })}
          </div>
          <div className="muted" style={{ fontSize: 11 }}>{job.activity || '…'}</div>
        </div>
      )}

      {/* proposal list */}
      {proposals.length > 0 && !detail && (
        <div className="rf-list">
          {proposals.map(o => (
            <div key={o.file} className="rf-row" onClick={() => select(o.file)}>
              <span className="jc">{o.file}</span>
              <span className="muted" style={{ fontSize: 10 }}>{(o.created_at || '').slice(5, 16)}</span>
              <span className={'pill ' + (o.status === 'adopted' ? 'up' : o.status === 'rejected' ? 'dn' : '')}>{STATUS_TXT[o.status] || o.status}</span>
            </div>
          ))}
        </div>
      )}

      {/* proposal detail: diff summary + proposed md + adopt/reject */}
      {detail && (
        <div className="rf-detail">
          <div className="rf-detail-head">
            <b>{detail.file}</b>
            <span className={'pill ' + (detail.diff?.status === 'adopted' ? 'up' : detail.diff?.status === 'rejected' ? 'dn' : '')}>{STATUS_TXT[detail.diff?.status] || detail.diff?.status || 'open'}</span>
            <button className="btn" style={{ marginLeft: 'auto' }} onClick={() => setDetail(null)}>關閉</button>
          </div>
          {diff && (
            <div className="rf-diffsum">
              <span className="pill up">＋{sec.added?.length || 0} 節</span>
              <span className="pill" style={{ color: 'var(--warn)' }}>改 {sec.changed?.length || 0} 節</span>
              <span className="pill dn">－{sec.removed?.length || 0} 節</span>
              <span className="muted" style={{ fontSize: 10 }}>大小 {diff.old_size}B → {diff.new_size}B · as_of {diff.as_of || '—'}</span>
            </div>
          )}
          {diff && (sec.added?.length > 0 || sec.changed?.length > 0 || sec.removed?.length > 0) && (
            <div className="rf-secdiff">
              {(sec.added || []).map(h => <div key={'a' + h} className="sd up">＋ {h}</div>)}
              {(sec.changed || []).map(h => <div key={'c' + h} className="sd">改 {h}</div>)}
              {(sec.removed || []).map(h => <div key={'r' + h} className="sd dn">－ {h}</div>)}
            </div>
          )}
          {diffLines.length > 0 && (
            <details className="rf-unified">
              <summary className="muted" style={{ fontSize: 11 }}>展開 unified diff（{diffLines.length} 行{diff.diff_truncated ? '…' : ''}）</summary>
              <pre>{diffLines.join('\n')}</pre>
            </details>
          )}
          {detail.text && (
            <div className="rf-proposed md" dangerouslySetInnerHTML={{ __html: mdToHtml(detail.text) }} />
          )}
          {(detail.diff?.status || 'open') === 'open' && (
            <div className="rf-actions">
              <button className="btn primary" onClick={() => act('adopt')} disabled={acting}>{acting ? '處理中…' : '採納'}</button>
              <button className="btn" onClick={() => act('reject')} disabled={acting}>拒絕</button>
            </div>
          )}
        </div>
      )}

      {/* timeline strip */}
      {timeline.length > 0 && (
        <div className="rf-timeline">
          <div className="muted" style={{ fontSize: 10 }}>改稿時間線</div>
          <div className="rf-tl-row">
            {timeline.map((r, i) => (
              <span key={i} className={'rf-tl ' + (r.action === 'adopt' ? 'up' : 'dn')}>
                <b>{(r.ts || '').slice(5, 16)}</b> {r.action === 'adopt' ? '採納' : '拒絕'} {r.proposal}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
