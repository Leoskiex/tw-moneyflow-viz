import React from 'react';
import { createRoot } from 'react-dom/client';
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom';
import './app.css';
import AppSkeleton from './AppSkeleton.jsx';
import Home from './pages/Home.jsx';
import Live from './pages/Live.jsx';
import SymbolCockpit from './pages/SymbolCockpit.jsx';
import SepaSymbolPage from './pages/SepaSymbolPage.jsx';
import Research from './pages/Research.jsx';
import Assistant from './pages/Assistant.jsx';
import Settings from './pages/Settings.jsx';
import SymbolSearch from './pages/SymbolSearch.jsx';
import FlowPage from './pages/FlowPage.jsx';
import WatchPage from './pages/WatchPage.jsx';
import BoardPage from './pages/BoardPage.jsx';
import HeatPage from './pages/HeatPage.jsx';

// Same route shapes as kansoku apps/web/src/generated-routes.ts (reimplemented, not copied):
// /  /symbol/:sym  /symbol/sepa/:sym  /research  /settings  /settings/:section
// + /live (INTRADAY_LIVE_WATCH)
// WAVE 2: /flow (D9 bubble), /watch (D7 NVIDIA), /board (F11 看圖版)
const routes = [
  { path: '/', element: <AppSkeleton><Home /></AppSkeleton> },
  { path: '/live', element: <AppSkeleton><Live /></AppSkeleton> },
  { path: '/flow', element: <AppSkeleton><FlowPage /></AppSkeleton> },
  { path: '/watch', element: <AppSkeleton><WatchPage /></AppSkeleton> },
  { path: '/board', element: <AppSkeleton><BoardPage /></AppSkeleton> },
  { path: '/heat', element: <AppSkeleton><HeatPage /></AppSkeleton> },
  { path: '/symbol', element: <AppSkeleton><SymbolSearch /></AppSkeleton> },
  { path: '/symbol/:sym', element: <AppSkeleton><SymbolCockpit /></AppSkeleton> },
  { path: '/symbol/sepa/:sym', element: <AppSkeleton><SepaSymbolPage /></AppSkeleton> },
  { path: '/research', element: <AppSkeleton><Research /></AppSkeleton> },
  { path: '/assistant', element: <AppSkeleton><Assistant /></AppSkeleton> },
  { path: '/settings', element: <AppSkeleton><Settings /></AppSkeleton> },
  { path: '/settings/:section', element: <AppSkeleton><Settings /></AppSkeleton> },
  { path: '*', element: <Navigate to="/" replace /> },
];
const router = createBrowserRouter(routes);

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>
);
