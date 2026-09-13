#!/bin/bash
# A4 runner: fetch fugle candles for the listed codes when their cache is older than 3 min.
ROOT="$HOME/Downloads/tw-moneyflow-viz"
cd "$ROOT" || exit 1
# env-only token (never in html)
[ -f "$ROOT/.env" ] && set -a && . "$ROOT/.env"
for CODE in "$@"; do
  [ -z "$CODE" ] && continue
  for TF in 5 15 60; do
    F="$ROOT/data/candles/${CODE}_${TF}m.json"
    STALE=1
    if [ -f "$F" ]; then
      M=$(stat -f "%m" "$F" 2>/dev/null || stat -c "%y" "$F")
      N=$(date +%s)
      [ $((N - M)) -le 180 ] && STALE=0
    fi
    if [ "$STALE" = "1" ]; then
      /usr/bin/python3 etl/fetch_fugle_candles.py --code "$CODE" --timeframe "$TF" >>/tmp/poll_fugle.log 2>&1
    fi
  done
done
exit 0
