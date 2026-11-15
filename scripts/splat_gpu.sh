#!/usr/bin/env bash
# The rented GPU that runs the splat builder (docs/SPLAT.md). Needs the `vastai` CLI, signed in.
#
#   scripts/splat_gpu.sh tunnel     keep http://127.0.0.1:8900 connected to the builder (leave it
#                                   running in its own terminal tab; it reconnects by itself)
#   scripts/splat_gpu.sh status     the instance, and whether the builder answers
#   scripts/splat_gpu.sh restart    restart the builder on the instance
#   scripts/splat_gpu.sh destroy    destroy the instance (stops the billing; asks first)
#
# The instance is found by its label, saveit-splat.
set -euo pipefail
LABEL="${SPLAT_LABEL:-saveit-splat}"
PORT="${SPLAT_PORT:-8900}"
KEY="${SPLAT_SSH_KEY:-$HOME/.ssh/id_ed25519}"

instance() {  # prints: <id> <public ip> <ssh port> <status>
  vastai show instances --raw 2>/dev/null | python3 -c '
import json, sys
label = sys.argv[1]
for row in json.load(sys.stdin):
    if row.get("label") == label:
        port = ((row.get("ports") or {}).get("22/tcp") or [{}])[0].get("HostPort", "")
        print(row["id"], row.get("public_ipaddr", ""), port, row.get("actual_status", ""))
        break
' "$LABEL"
}

read -r ID HOST SSH_PORT STATE <<<"$(instance)" || true
if [ -z "${ID:-}" ]; then
  echo "no Vast.ai instance labelled $LABEL (see docs/SPLAT.md to rent one)" >&2
  exit 1
fi
SSH=(ssh -p "$SSH_PORT" -i "$KEY" -o ConnectTimeout=20 -o ServerAliveInterval=15
     -o ServerAliveCountMax=4 -o StrictHostKeyChecking=accept-new "root@$HOST")

case "${1:-status}" in
  tunnel)
    echo "tunnel: http://127.0.0.1:$PORT -> instance $ID ($HOST). Ctrl-C to stop."
    while true; do
      "${SSH[@]}" -N -o ExitOnForwardFailure=yes -L "$PORT:127.0.0.1:8900" || true
      echo "$(date +%H:%M:%S) tunnel dropped; reconnecting in 2 s" >&2
      sleep 2
    done
    ;;
  status)
    echo "instance $ID: $STATE at $HOST:$SSH_PORT"
    curl -s -m 5 "http://127.0.0.1:$PORT/health" || echo "no builder at 127.0.0.1:$PORT (run: scripts/splat_gpu.sh tunnel)"
    echo
    ;;
  restart)
    "${SSH[@]}" 'bash /workspace/splat-builder/splat/run.sh'
    ;;
  destroy)
    read -r -p "Destroy instance $ID and everything on it? [y/N] " answer
    [ "$answer" = "y" ] && vastai destroy instance "$ID"
    ;;
  *)
    echo "usage: scripts/splat_gpu.sh tunnel|status|restart|destroy" >&2
    exit 2
    ;;
esac
