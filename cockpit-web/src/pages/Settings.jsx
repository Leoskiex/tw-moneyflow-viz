import { useState } from 'react';
import { useTpeClock } from '../lib/clock.js';

// /settings — model slots + Asia/Taipei clock (like kansoku settings shot).
// No keys in the frontend: credentials live in Mac env (FINMIND/FUGLE/LLM on :8790 helper).
export default function Settings() {
  const clock = useTpeClock();
  const [llmUrl, setLlmUrl] = useState(localStorage.getItem('kdw:llmUrl') || 'http://192.168.31.151:8888/v1');
  const [model, setModel] = useState(localStorage.getItem('kdw:llmModel') || 'qwen3.8-flash-next');

  return (
    <div className="page narrow settings">
      <div className="topstrip">
        <div>
          <div className="hs">設置</div>
          <div className="muted">本地模型設定（credentials 留在 Mac env，前端不存 key）</div>
        </div>
        <span className="pill" style={{ color: 'var(--accent)' }}>{clock}</span>
      </div>

      <div className="card" style={{ marginBottom: 14 }}>
        <h3>本地 LLM（helper :8790 使用 head）</h3>
        <div className="kv" style={{ padding: 12 }}>
          <div className="kvrow"><span>head</span><b>127.0.0.1:8888 · {model} <i className="muted">（vLLM）</i></b></div>
          <div className="kvrow"><span>helper 實連</span><b>192.168.31.151:8888/v1（Mac 經 LAN 連 head）</b></div>
          <div className="kvrow"><span>worker</span><b className="muted">192.168.31.211:8888（SGLang，備用）</b></div>
          <label className="fld"><span className="muted">偏好記錄（本地 localStorage，不存 key）</span>
            <input value={model} onChange={e => setModel(e.target.value)} onBlur={() => localStorage.setItem('kdw:llmModel', model)} /></label>
          <div className="muted" style={{ marginTop: 8 }}>
            helper 由 env COCKPIT_LLM_URL / COCKPIT_LLM_MODEL 決定；預設 head vLLM + qwen3.8-flash-next。credentials 只住 Mac env，前端不存 key。
          </div>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 14 }}>
        <h3>時區 / 時鐘</h3>
        <div className="kv" style={{ padding: 12 }}>
          <div className="kvrow"><span>顯示時區</span><b>Asia/Taipei（TW 09:00–13:30 session）</b></div>
          <div className="kvrow"><span>現在</span><b>{clock}</b></div>
        </div>
      </div>

      <div className="card">
        <h3>資料來源（只讀，無寫入）</h3>
        <div className="kv" style={{ padding: 12 }}>
          <div className="kvrow"><span>日K / 分K</span><b>data/candles（:8790 on-demand）</b></div>
          <div className="kvrow"><span>法人</span><b>FundFlo latest.json（T−1，只讀）</b></div>
          <div className="kvrow"><span>凍結點評</span><b>data/cockpit/cockpit.jsonl</b></div>
          <div className="kvrow"><span>即時 AI</span><b>:8790 /ask（本機 vLLM）</b></div>
          <div className="kvrow"><span>Live 5m</span><b>data/live（etl/live_watch.py，launchd）</b></div>
        </div>
      </div>
    </div>
  );
}
