#!/usr/bin/env python3
"""P2 watcher: compare the last Fugle 5m bar with frozen triggers; notify via osascript."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"


def main():
    p = DATA / "cockpit" / "cockpit.jsonl"
    if not p.exists():
        return 0
    rows = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except Exception:
                continue
    if not rows:
        return 0
    last = rows[-1]
    code = last.get("code")
    five = DATA / "candles" / f"{code}_5m.json"
    if not five.exists():
        return 0
    doc = json.loads(five.read_text(encoding="utf-8"))
    block = (doc.get("timeframes") or {}).get("5m") or {}
    bars = block.get("bars") or []
    if not bars:
        return 0
    px = bars[-1]["close"]
    scn = last.get("scenarios") or {}
    bull, bear = scn.get("bull"), scn.get("bear")
    msg = []
    if bull and px >= bull:
        msg.append(f"{code} 5m {px} 觸發看多 {bull}")
    if bear and px <= bear:
        msg.append(f"{code} 5m {px} 觸發看空 {bear}")
    if not msg:
        return 0
    import subprocess
    body = "；".join(msg)
    subprocess.run(["/usr/bin/osascript", "-e",
                    f'display notification "{body}" with title "Cockpit 觸發"',
                    ], timeout=20)
    print(body)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
