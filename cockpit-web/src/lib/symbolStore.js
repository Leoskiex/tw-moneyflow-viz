// Symbol view-state shared across cockpit ⇄ SEPA so the same code keeps its
// chart state when switching (kansoku keeps doc state per symbol in-context).
const store = {};
export function viewState(code) {
  store[code] ||= { tf: '1D', overlays: { ma: true, macd: true, piv: true, rsi: true, kd: false, boll: false, mark: true, draw: false } };
  return store[code];
}
// Recently opened symbols (QuickBar "最近" row)
export function pushRecent(code) {
  try {
    const k = 'kdw:recent';
    const list = (JSON.parse(localStorage.getItem(k) || '[]').filter(x => x !== code));
    list.unshift(code);
    localStorage.setItem(k, JSON.stringify(list.slice(0, 12)));
  } catch (_) {}
}
export function listRecent() {
  try { return JSON.parse(localStorage.getItem('kdw:recent') || '[]'); } catch (_) { return []; }
}
