#!/usr/bin/env bash
# Expose the local /ws server to Prosper. Paste the printed wss://…/ws into the dashboard:
# Settings → Integration → Endpoint (it applies to the next run).
#
#   scripts/tunnel.sh                         # ngrok if installed, else cloudflared quick tunnel
#   NGROK_DOMAIN=name.ngrok-free.app scripts/tunnel.sh   # static ngrok domain: survives restarts
set -euo pipefail
PORT="${PORT:-7860}"

if command -v ngrok >/dev/null 2>&1; then
  if [[ -n "${NGROK_DOMAIN:-}" ]]; then
    echo "Endpoint: wss://${NGROK_DOMAIN}/ws"
    exec ngrok http --url="${NGROK_DOMAIN}" "${PORT}"
  fi
  echo "Endpoint: wss://<the https host ngrok prints>/ws  (a free URL changes on every restart)"
  exec ngrok http "${PORT}"
elif command -v cloudflared >/dev/null 2>&1; then
  echo "Endpoint: wss://<the trycloudflare.com host printed below>/ws  (changes on every restart)"
  exec cloudflared tunnel --url "http://localhost:${PORT}"
else
  echo "No tunnel installed: brew install ngrok (then: ngrok config add-authtoken <token>)" >&2
  echo "or: brew install cloudflared (no account needed)" >&2
  exit 1
fi
