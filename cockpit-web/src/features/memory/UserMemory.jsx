import { useEffect, useState } from 'react';
import { memoryGet, memorySave, memoryClear } from '../../lib/data.js';

// D4 P1 長期記憶 — user-level memory editor (設置).
// Fields: risk_pref (風險偏好), watch_notes (觀察備註, 分號), rules (規則, 分號, 如「禁止亂編」).
// Persisted to data/memory/user.json via :8790 /memory. Injected into /ask & /p2 for every code.
export default function UserMemory() {
  const [riskPref, setRiskPref] = useState('');
  const [watchNotes, setWatchNotes] = useState('');
  const [rules, setRules] = useState('');
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState('');

  const load = async () => {
    const d = await memoryGet();
    setRiskPref(d.user?.risk_pref || '');
    setWatchNotes((d.user?.watch_notes || []).join('；'));
    setRules((d.user?.rules || []).join('；'));
  };
  useEffect(() => { load(); }, []); // eslint-disable-line

  const save = async () => {
    setBusy(true); setNote('');
    const data = {};
    if (riskPref.trim()) data.risk_pref = riskPref.trim();
    if (watchNotes.trim()) data.watch_notes = watchNotes.split(/[;；]/).map(s => s.trim()).filter(Boolean);
    if (rules.trim()) data.rules = rules.split(/[;；]/).map(s => s.trim()).filter(Boolean);
    const r = await memorySave('user', data);
    setBusy(false);
    if (r.ok) { setNote('已存 memory/user.json（/ask · /p2 全代碼注入）'); await load(); }
    else setNote(r.error || '保存失敗');
  };
  const clear = async () => {
    setBusy(true); setNote('');
    const r = await memoryClear('user');
    setBusy(false);
    if (r.ok) { setRiskPref(''); setWatchNotes(''); setRules(''); setNote('已清除用戶記憶'); }
    else setNote(r.error || '清除失敗');
  };

  return (
    <div className="card" style={{ marginBottom: 14 }}>
      <div className="mem-head">
        <h3>長期記憶（用戶）</h3>
        <div className="mem-btns">
          <button className="btn" onClick={save} disabled={busy}>{busy ? '…' : '存用戶記憶'}</button>
          <button className="btn" onClick={clear} disabled={busy}>清除</button>
        </div>
      </div>
      <div className="kv" style={{ padding: 12 }}>
        <label className="fld"><span className="muted">風險偏好</span>
          <input value={riskPref} onChange={e => setRiskPref(e.target.value)} placeholder="例：偏穩健，重回撤、不追高" /></label>
        <label className="fld"><span className="muted">觀察備註（分號分隔）</span>
          <input value={watchNotes} onChange={e => setWatchNotes(e.target.value)} placeholder="例：2330 外資回流；2454 看 150 壓力" /></label>
        <label className="fld"><span className="muted">規則（分號分隔）</span>
          <input value={rules} onChange={e => setRules(e.target.value)} placeholder="例：禁止亂編；引用欄位不得造數" /></label>
        {note && <div className="muted" style={{ fontSize: 11 }}>{note}</div>}
        <div className="muted" style={{ fontSize: 10, marginTop: 4 }}>
          存於 data/memory/user.json；前端無 key。/ask 與 /p2 會對每個代碼自動注入這份記憶（檔案缺則空，助手照常運作）。
        </div>
      </div>
    </div>
  );
}
