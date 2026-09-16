import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { jget, DATA } from '../lib/data.js';
import FundRank from '../features/story/FundRank.jsx';
import BubbleFlow from '../features/flow/BubbleFlow.jsx';

// D9 surface — 盤面 /flow: 四象限泡泡 + D1 水流排行（same book data/fundflo）.
// :8777/fund-flow.html 302 → here (not an empty shell).
export default function FlowPage() {
  const [ff, setFF] = useState(null);
  useEffect(() => { jget(DATA('data/fundflo/latest.json')).then(setFF); }, []);
  return (
    <div className="page flowpage">
      <div className="fb-top">
        <div>
          <div className="hs">錢怎麼流 · 盤面</div>
          <div className="muted">四象限泡泡（F03）＋ 水流排行（F02）· 讀同一 data/fundflo 序列 · {ff?.meta?.date || '—'}</div>
        </div>
        <Link className="pill" to="/">← 回今日</Link>
      </div>
      <div className="fb-bubble-mount">
        <BubbleFlow />
      </div>
      <FundRank />
    </div>
  );
}
