import { useEffect, useState } from 'react';

// Asia/Taipei wall clock in the titlebar (their settings show a TZ card; we keep it live).
export function useTpeClock() {
  const [now, setNow] = useState(() => tpeNow());
  useEffect(() => {
    const id = setInterval(() => setNow(tpeNow()), 1000);
    return () => clearInterval(id);
  }, []);
  return now;
}
function tpeNow() {
  const s = new Date().toLocaleTimeString('en-GB', { timeZone: 'Asia/Taipei', hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  const d = new Date().toLocaleDateString('en-CA', { timeZone: 'Asia/Taipei' });
  return `${d} ${s} TPE`;
}
