import { Link, useLocation } from 'react-router-dom';
import { useTpeClock } from './lib/clock.js';

// One persistent chrome for the whole app — mirrors kansoku AppSkeleton.tsx
// (fixed titlebar + tabstrip; content area swaps without a full reload).
// 8 tabs (WAVE 2 adds 觀察 per docs/NVIDIA_WATCH_PAGE.md §3):
// 今日(/) · 盤中(/live) · 觀察(/watch) · 個股(搜尋→/symbol/:code) ·
// SEPA(/symbol/sepa/:code) · 研究庫 · 助理 · 設置.
const TABS = [
  { to: '/', label: '今日', end: true },
  { to: '/live', label: '盤中' },
  { to: '/watch', label: '觀察' },
  { to: '/symbol', label: '個股' },
  { to: '/sepa', label: 'SEPA' },
  { to: '/research', label: '研究庫' },
  { to: '/assistant', label: '助理' },
  { to: '/settings', label: '設置' },
];

function activeKey(pathname) {
  if (pathname === '/' || pathname.startsWith('/live')) return pathname;
  if (pathname.startsWith('/watch')) return '/watch';
  if (pathname.startsWith('/symbol/sepa/')) return '/sepa';
  if (pathname.startsWith('/symbol/')) return '/symbol';
  if (pathname.startsWith('/research')) return '/research';
  if (pathname.startsWith('/assistant')) return '/assistant';
  if (pathname.startsWith('/settings')) return '/settings';
  return pathname;
}

export default function AppSkeleton({ children, right }) {
  const clock = useTpeClock();
  const { pathname } = useLocation();
  const cur = activeKey(pathname);
  // 個股 / SEPA tabs: keep the code from the URL when present, else land on search.
  const m = pathname.match(/^\/symbol(?:\/sepa)?\/([^/]+)/);
  const sym = m ? m[1] : null;
  const symTab = sym ? `/symbol/${sym}` : '/symbol';
  const sepaTab = sym ? `/symbol/sepa/${sym}` : '/sepa';
  const hrefOf = (t) => (t.to === '/symbol' ? symTab : t.to === '/sepa' ? sepaTab : t.to);

  return (
    <div className="app-root">
      <div className="titlebar">
        <div className="brand">Kansoku TW</div>
        <nav className="tabstrip" aria-label="main">
          {TABS.map(t => (
            <Link key={t.to} to={hrefOf(t)}
              className={'tab' + (cur === activeKey(t.to) ? ' active' : '')}>
              {t.label}
            </Link>
          ))}
        </nav>
        <div className="titlebar-right">
          {right}
          <span className="tpe" title="Asia/Taipei">{clock}</span>
        </div>
      </div>
      <main className="app-content">{children}</main>
    </div>
  );
}

