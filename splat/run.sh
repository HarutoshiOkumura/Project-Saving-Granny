#!/usr/bin/env bash
# Start (or restart) the splat builder on the GPU machine and wait until it answers.
#   bash splat/run.sh          from the folder that holds splat/ and AnySplat/
# It listens on 127.0.0.1:8900 only; reach it from the laptop with
#   ssh -N -L 8900:127.0.0.1:8900 -p <port> root@<host>
set -euo pipefail
cd "$(dirname "$0")/.."
export SPLAT_ANYSPLAT_DIR="${SPLAT_ANYSPLAT_DIR:-$PWD/AnySplat}"
if [ -f server.pid ] && kill -0 "$(cat server.pid)" 2>/dev/null; then
  kill "$(cat server.pid)"
  sleep 1
fi
nohup python -m splat.server > server.log 2>&1 < /dev/null &
echo $! > server.pid
for _ in $(seq 1 90); do
  if curl -s -m 2 "http://127.0.0.1:${SPLAT_PORT:-8900}/health"; then
    echo
    exit 0
  fi
  kill -0 "$(cat server.pid)" 2>/dev/null || { tail -20 server.log; exit 1; }
  sleep 2
done
tail -20 server.log
exit 1
