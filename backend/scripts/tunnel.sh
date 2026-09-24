#!/usr/bin/env bash
# Expose the local voice server so Twilio can reach it: point the number's voice webhook at
# https://<host>/integrations/twilio/voice (the media stream follows on /integrations/twilio/ws).
#
#   scripts/tunnel.sh                         # ngrok if installed, else cloudflared quick tunnel
#   NGROK_DOMAIN=name.ngrok-free.app scripts/tunnel.sh   # static ngrok domain: survives restarts
set -euo pipefail
PORT="${PORT:-7860}"

if command -v ngrok >/dev/null 2>&1; then
  if [[ -n "${NGROK_DOMAIN:-}" ]]; then
    echo "Webhook: https://${NGROK_DOMAIN}/integrations/twilio/voice"
    exec ngrok http --url="${NGROK_DOMAIN}" "${PORT}"
  fi
  echo "Webhook: https://<the https host ngrok prints>/integrations/twilio/voice  (a free URL changes on every restart)"
  exec ngrok http "${PORT}"
elif command -v cloudflared >/dev/null 2>&1; then
  echo "Webhook: https://<the trycloudflare.com host printed below>/integrations/twilio/voice  (changes on every restart)"
  exec cloudflared tunnel --url "http://localhost:${PORT}"
else
  echo "No tunnel installed: brew install ngrok (then: ngrok config add-authtoken <token>)" >&2
  echo "or: brew install cloudflared (no account needed)" >&2
  exit 1
fi
