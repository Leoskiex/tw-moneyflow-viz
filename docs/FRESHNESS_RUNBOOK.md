# Freshness runbook — TW cockpit data & helpers

**As of:** 2026-09-17 TPE · CoS  
**Goal:** Keep day-end FundFlo / FinMind dailies / Fugle session poll / `:8790` helper alive across reboots **without** pasting secrets, and without fighting macOS TCC forever.

---

## 0. What “fresh” means

| Surface | Source | Cadence | Healthy when |
|--------|--------|---------|--------------|
| FundFlo / 今日 / 熱力 / 泡泡 | `twse-trading` T86 + overlays → `build_fundflo_features` | Post-close (~21:10) | `data/fundflo/latest.json` `meta.date` = last trade day; `data/refresh_status.json` `ok: true` |
| FinMind daily bars | `etl/finmind_batch.py` / `run_daily.py` | Nightly | `data/candles/<code>_daily.json` last bar = last trade day (≥200 bars) |
| Fugle 5m/15m/60m | `:8790` on-search + `poll_fugle` watchlist≤60 | Session | Opened codes’ `*_5m.json` mtime within ~3–30 min while visible |
| CMI weather badge | FundFlo overlay → Day Operator JSON | Post-close | `data/cmi/day_operator_latest.json` `as_of*` matches trade day |
| SPA `:8778` | `cockpit-web-dist` via launchd | Always | `http://127.0.0.1:8778/` 200 |
| Helper `:8790` | `etl/candle_server.py` | Always | `/status` responds (even 400 body is “up”); `/fetch` `/ask` `/research-deep` `/memory` `/watch/*` |

**Keys stay in Mac env** (`~/trading-workspace/.env` or shell profile). Never in HTML / SPA / git.

---

## 1. The real wall: TCC on `~/Downloads`

LaunchAgents **cannot reliably read/write** `~/Downloads/...` (TCC “Operation not permitted”). That is why:

- `com.leoskie.tw-moneyflow.8790` was **booted out** / missing from `launchctl print`
- FinMind nightly from launchd fails when rooted in Downloads
- SPA was already moved to **Application Support** (`cockpit-web-dist` + `spa_8778.py`) — that path works

**Two durable fixes (pick one):**

### Path A — Relocate (preferred, no FDA click)

Move the **runtime tree** out of Downloads into:

`~/Library/Application Support/tw-moneyflow/runtime/`

Suggested layout:

```text
~/Library/Application Support/tw-moneyflow/
  cockpit-web-dist/          # already (8778)
  bin/spa_8778.py            # already
  runtime/                   # NEW — viz root for helpers + data
    etl/
    data/                    # candles, fundflo symlinks or copies, memory, research, live
    docs/                    # optional
  tw-moneyflow-viz.git/      # push clone (already)
```

Then point **all** LaunchAgents’ `WorkingDirectory` + script paths at `runtime/`, not Downloads.

Keep `~/Downloads/tw-moneyflow-viz` as a **dev checkout** if you want, but launchd must not use it.

**One-shot migrate (run in Terminal.app, not over plain ssh if possible):**

```bash
AS="$HOME/Library/Application Support/tw-moneyflow"
SRC="$HOME/Downloads/tw-moneyflow-viz"
mkdir -p "$AS/runtime"
# rsync code + data (candles ~90MB — expect a few minutes)
rsync -a --delete \
  --exclude '.git' --exclude 'node_modules' --exclude 'cockpit-web/node_modules' \
  "$SRC/" "$AS/runtime/"
# env: do NOT copy secrets into git; ensure helper reads:
#   ~/trading-workspace/.env  OR  $AS/runtime/.env (chmod 600, gitignored)
```

Update plists (8790, finmind.batch, p3.poll, livewatch, stale-watch, 8777 if still used) so every `ProgramArguments` path and `WorkingDirectory` uses `$AS/runtime`.

Reload:

```bash
UID_N=$(id -u)
for L in com.leoskie.tw-moneyflow.8790 com.leoskie.finmind.batch com.leoskie.p3.poll \
         com.leoskie.tw-moneyflow.livewatch com.leoskie.tw-moneyflow.stale-watch; do
  launchctl bootout "gui/$UID_N/$L" 2>/dev/null
  launchctl bootstrap "gui/$UID_N" "$HOME/Library/LaunchAgents/$L.plist"
  launchctl enable "gui/$UID_N/$L" 2>/dev/null
done
launchctl kickstart -k "gui/$UID_N/com.leoskie.tw-moneyflow.8790"
curl -sS -o /dev/null -w '8790 %{http_code}\n' --max-time 3 http://127.0.0.1:8790/status
```

### Path B — Full Disk Access (keep Downloads)

System Settings → Privacy & Security → **Full Disk Access** → enable for:

- `/usr/bin/python3` (or the exact python the plists use)
- **Terminal** (if you debug interactively)
- Optionally **Cursor** / local coding agent host

Then `launchctl bootstrap` the 8790 plist again. Re-test after reboot.

FDA does **not** replace Path A forever — App Support is still cleaner for LaunchAgents.

---

## 2. Helper `:8790` steady-state checklist

```bash
# Is something listening?
lsof -iTCP:8790 -sTCP:LISTEN -P
# Launchd know about it?
launchctl print "gui/$(id -u)/com.leoskie.tw-moneyflow.8790" | head -30
# Manual start (until launchd fixed) — TCC-safe cwd:
cd "$HOME/Library/Application Support/tw-moneyflow/runtime"  # or Downloads until migrated
nohup /usr/bin/python3 -u etl/candle_server.py >/tmp/candle_helper.out 2>/tmp/candle_helper.err &
```

**Pass:** `curl http://127.0.0.1:8790/status` returns quickly (any HTTP code with body).  
**Fail:** hang / connection refused after reboot → plist still on Downloads or FDA missing.

Plist template must bind LAN the same way the working process does (`0.0.0.0`, CORS open for home LAN). Keys only via env.

---

## 3. FinMind nightly (dailies)

- Job: `com.leoskie.finmind.batch` → `etl/run_daily.py` @ **21:10** local
- Must run from **TCC-safe root** (Path A) or with FDA (Path B)
- Env: `FINMIND_TOKEN` (or project’s name) from `~/trading-workspace/.env`
- Rate: prefer one API call per date for all names (~600/hr); append last trade day only after backfill

**Verify:**

```bash
python3 - <<'PY'
from pathlib import Path
import json
from datetime import datetime
root=Path.home()/"Library/Application Support/tw-moneyflow/runtime"  # or Downloads path
for code in ["0050","2330","2454"]:
  p=root/f"data/candles/{code}_daily.json"
  j=json.loads(p.read_text())
  bars=j if isinstance(j,list) else j.get("data") or j.get("bars") or []
  last=(bars[-1].get("date") or bars[-1].get("time")) if bars else None
  print(code, "n=", len(bars), "last=", last, "mtime=", datetime.fromtimestamp(p.stat().st_mtime))
PY
tail -50 /tmp/tw_daily.log
```

---

## 4. Fugle session poll (watchlist ≤60)

- Job: `com.leoskie.p3.poll` → `etl/poll_fugle.py` every **30s** (or `poll_fugle.sh`)
- **Output must be the same tree the SPA / `:8790` / `:8777` serve** — historically a bug wrote under `Application Support/tw-moneyflow/data/candles` while UI read `Downloads/.../data/candles`
- After Path A migrate, both should be `$AS/runtime/data/candles`
- Source env from `~/trading-workspace/.env` (`FUGLE_API_KEY`), not a missing `$ROOT/.env`
- Cap watchlist ≤60 (product rule)

**Verify in session:**

```bash
ls -lt "$ROOT/data/candles/"*_5m.json | head
# open :8778/symbol/2454 — should stay fresh while tab visible
```

---

## 5. FundFlo / T86 day-end

Orchestrator lives under `~/Downloads/twse-trading` (`refresh_daily.py` etc.). Last known good pattern:

- Fetch T86 + related TWSE dumps → curated → `build_fundflo_features` → screens / regime / digest
- Also export `regime_overlay_daily.csv` into viz `data/cmi/` (AISTOCKMAP hook)

**Verify:**

```bash
python3 -c "import json; j=json.load(open('data/refresh_status.json')); print(j['trade_day'], j['ok'], j['finished'])"
python3 -c "import json; print(json.load(open('data/fundflo/latest.json'))['meta']['date'])"
```

If `by_date/` empty or `ok: false` on `T86`: restore fetch credentials / network, re-run `refresh_daily` from Terminal (not launchd-on-Downloads).

**CMI:** after FundFlo OK, refresh Day Operator → copy `day_operator_latest.json` into viz `data/cmi/` for the SPA badge.

---

## 6. Reboot acceptance (5 minutes)

1. `:8778/` 200  
2. `:8790/status` up **via launchd** (not only leftover nohup)  
3. `launchctl print gui/$UID/com.leoskie.tw-moneyflow.8790` shows running  
4. Open `/symbol/2454` — fetch works if 5m stale  
5. After a trade day evening: FundFlo `meta.date` + FinMind daily last bar match that day  

---

## 7. Do / Don’t

| Do | Don’t |
|----|-------|
| Run launchd from Application Support | Point KeepAlive helpers at `~/Downloads` |
| Keep keys in env / 600 `.env` gitignored | Paste PAT / FinMind / Fugle into chat or SPA |
| Push code via Mini `gh` as Leoskiex | Put `ghp_` in remote URL or `.env` committed |
| Symlink topic SoT `TW_TOPIC_MEMBERS.json` across map/FundFlo/SPA | Invent a second industry book |

---

## 8. When to ask a human

- First-time **Full Disk Access** toggle (Path B)
- First **rsync migrate** if disk space / which tree is canonical is unclear
- GitHub `gh auth login` if keyring dies (`re-login done` after browser login)

Coding agents: implement Path A plist rewrites + verify scripts; **stop** before claiming FDA — that click is human-only.
