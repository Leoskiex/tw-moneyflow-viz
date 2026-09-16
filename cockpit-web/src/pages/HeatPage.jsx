import { Link } from 'react-router-dom';
import HeatTw from '../features/heat/HeatTw.jsx';

// /heat — D3 台股熱力 full route (same AppSkeleton as /flow, /board).
export default function HeatPage() {
  return (
    <div className="page heatpage">
      <div className="topstrip">
        <div>
          <div className="hs">台股熱力 · 題材 × 錢</div>
          <div className="muted">SoT 主題格子 — 顏色＝FundFlo 流入／流出（綠進紅出），點格子看個股</div>
        </div>
        <div className="strip-right">
          <Link to="/flow" className="pill" style={{ color: 'var(--accent)' }}>盤面 泡泡 →</Link>
          <Link to="/" className="pill">今日 →</Link>
        </div>
      </div>
      <HeatTw />
    </div>
  );
}
