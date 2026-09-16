import { useEffect, useState } from 'react';
import { memoryGet, memorySave, memoryClear } from '../../lib/data.js';

// D4 P1 長期記憶 — per-symbol memory block (個股右欄).
// Fields: last_takeaway (上次結論), levels_of_interest (關注位, 分號分隔), user_notes (筆記).
// Persisted to data/memory/symbols/<code>.json via :8790 /memory. Injected into /ask & /p2.
export default function SymbolMemory({ code }) {
  const [sym, setSym] = useState(null);
  const [takeaway, setTakeaway] = useState('');
  const [levels, setLevels] = useState('');
  const [notes, setNotes] = useState('');
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState('');

  const load = async () => {
    const d = await memoryGet(code);
    setSym(d.symbol);
    setTakeaway(d.symbol?.last_takeaway || '');
    setLevels((d.symbol?.levels_of_interest || []).join('；'));
    setNotes((d.symbol?.user_notes || []).join('；'));
  };
  useEffect(() => { setNote(''); load(); }, [code]); // eslint-disable-line

  const save = async () => {
    setBusy(true); setNote('');
    const data = {};
    if (takeaway.trim()) data.last_takeaway = takeaway.trim();
    if (levels.trim()) data.levels_of_interest = levels.split(/[;；]/).map(s => s.trim()).filter(Boolean);
    if (notes.trim()) data.user_notes = notes.split(/[;；]/).map(s => s.trim()).filter(Boolean);
    const r = await memorySave('symbol', data, code);
    setBusy(false);
    if (r.ok) { setNote('已存 memory/symbols/' + code + '.json'); await load(); }
    else setNote(r.error || '保存失敗');
  };
  const clear = async () => {
    setBusy(true); setNote('');
    const r = await memoryClear('symbol', code);
    setBusy(false);
    if (r.ok) { setTakeaway(''); setLevels(''); setNotes(''); setNote('已清除 ' + code + ' 記憶'); }
    else setNote(r.error || '清除失敗');
  };

  return (
    <div className="symmem">
      <div className="symmem-head">
        <b>本碼記憶（/ask · /p2 自動注入）</b>
        <div className="symmem-btns">
          <button className="btn" onClick={save} disabled={busy}>{busy ? '…' : '存'}</button>
          <button className="btn" onClick={clear} disabled={busy}>清除</button>
        </div>
      </div>
      <label className="fld"><span className="muted">上次結論</span>
        <input value={takeaway} onChange={e => setTakeaway(e.target.value)} placeholder="例：ma50 失守，等回測確認" /></label>
      <label className="fld"><span className="muted">關注位（分號分隔）</span>
        <input value={levels} onChange={e => setLevels(e.target.value)} placeholder="例：145 壓力；138 支撐" /></label>
      <label className="fld"><span className="muted">用戶筆記</span>
        <textarea rows="2" value={notes} onChange={e => setNotes(e.target.value)} placeholder="本碼觀察筆記" /></label>
      {note && <div className="muted" style={{ fontSize: 11 }}>{note}</div>}
      <div className="muted" style={{ fontSize: 10, marginTop: 4 }}>存於 data/memory/symbols/{code}.json（前端無 key）</div>
    </div>
  );
}
