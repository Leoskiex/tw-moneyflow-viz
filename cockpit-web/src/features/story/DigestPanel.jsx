import { useEffect, useState } from 'react';
import { jget, DATA, mdToHtml } from '../../lib/data.js';

// 制式日報 (F10) — digest_latest.json (.markdown) rendered on 今日 as a panel.
// Same digest JSON as digest.html; no LLM in the path.
export default function DigestPanel() {
  const [d, setD] = useState(null);
  const [open, setOpen] = useState(false);
  useEffect(() => { jget(DATA('data/digest_latest.json')).then(setD); }, []);

  if (!d) return null;
  return (
    <div className="digestpanel">
      <button className="dp-head" onClick={() => setOpen(o => !o)} aria-expanded={open}>
        <span className="dp-title">制式日報 <span className="muted">{d.date}</span></span>
        {d.headline && <span className="dp-headline muted">{d.headline}</span>}
        <span className="muted">{open ? '收起 ▲' : '展開 ▼'}</span>
      </button>
      {open && (
        <div className="dp-body" dangerouslySetInnerHTML={{ __html: mdToHtml(d.markdown || '') }} />
      )}
    </div>
  );
}
