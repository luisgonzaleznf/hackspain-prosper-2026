#!/usr/bin/env bash
# Keep the Prosper endpoint DISCONNECTED except while we are actively running something
# (a practice call, a Switchboard burst, a Run All). See "Endpoint policy" in AGENTS.md.
#
#   scripts/endpoint.sh session [VOICE] [PORT]   # connect, wait for the calls, auto-disconnect when idle
#   scripts/endpoint.sh up      [VOICE] [PORT]   # connect: agent server (started if needed) + tunnel
#   scripts/endpoint.sh down    [--all]          # disconnect: close our tunnel (--all: every tunnel + our server)
#   scripts/endpoint.sh status                   # what is running and whether Prosper can reach it
#
# VOICE is REQUIRED (codex|gemini|gptlive|none): no default, so nobody opens the line on a voice
# that cannot talk (Gemini out of credits, GPT-Live refusing sessions). PORT defaults to 7860.
#   NGROK_DOMAIN=<name>.ngrok-free.app   stable address: save wss://<domain>/ws on the dashboard ONCE.
#   Without it: a cloudflared quick tunnel, whose address is NEW on every `up`, so it has to be saved
#   in Settings → Integration before each run (a run snapshots the endpoint when it is admitted).
#   IDLE_SECS=90         session: disconnect after this long with no active call
#   FIRST_CALL_SECS=900  session: disconnect if no call arrives within this long of connecting
#   MAX_SECS=5400        session: hard ceiling
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STATE_DIR="$ROOT/logs/endpoint"
STATE="$STATE_DIR/state"
EVENTS="$STATE_DIR/events.log"
mkdir -p "$STATE_DIR"

say() { printf '%s %s\n' "$(date '+%H:%M:%S')" "$*"; }
event() { printf '%s %s\n' "$(date '+%Y-%m-%dT%H:%M:%S%z')" "$*" >> "$EVENTS"; }
alive() { [ -n "${1:-}" ] && kill -0 "$1" 2>/dev/null; }
state_get() { [ -f "$STATE" ] && sed -n "s/^$1=//p" "$STATE" | tail -1; }

local_health() {  # prints "voice active_calls" or nothing
  curl -s -m 3 "http://localhost:$1/health" 2>/dev/null | python3 -c \
    'import json,sys
try:
    d=json.load(sys.stdin); print(d.get("voice",""), d.get("active_calls",0))
except Exception:
    pass'
}

public_ip() {  # resolve via public DNS: the local resolver caches "no such host" for new tunnels
  dig +short "$1" @1.1.1.1 2>/dev/null | grep -E '^[0-9.]+$' | head -1
}

public_health_code() {  # HTTP status of https://HOST/health as Prosper would see it
  local host=$1 ip
  ip=$(public_ip "$host")
  [ -z "$ip" ] && { echo 000; return; }
  curl -s -o /dev/null -m 8 -w '%{http_code}' --resolve "$host:443:$ip" "https://$host/health"
}

public_ws_ok() {
  # An accepted upgrade keeps the socket open, so curl always ends on its -m timeout (exit 28):
  # judge the status line it printed, never curl's exit code (pipefail would turn 28 into "down").
  local host=$1 ip line
  ip=$(public_ip "$host")
  [ -z "$ip" ] && return 1
  line=$(curl -s -m 4 -i --http1.1 --resolve "$host:443:$ip" -H "Connection: Upgrade" \
    -H "Upgrade: websocket" -H "Sec-WebSocket-Version: 13" \
    -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" "https://$host/ws" 2>/dev/null | head -1) || true
  case "$line" in *" 101 "*) return 0 ;; *) return 1 ;; esac
}

other_tunnels() {  # processes whose program IS cloudflared/ngrok, not shells that mention them
  ps -axo pid=,args= | awk '{n=split($2,a,"/"); b=a[n]; if ((b=="cloudflared" && $3=="tunnel") || (b=="ngrok" && ($3=="http" || $3=="start"))) print}'
}

require_voice() {  # $1 voice, $2 command name
  case "${1:-}" in
    codex|gemini|gptlive|none) return 0 ;;
    "") say "ERROR: name the voice: scripts/endpoint.sh $2 codex|gemini [PORT]. There is no default:" \
          "check that voice's access/credits first." ;;
    *) say "ERROR: unknown voice '$1' (codex|gemini|gptlive|none)." ;;
  esac
  return 2
}

ensure_server() {  # $1 voice, $2 port; starts one if nothing listens there
  local voice=$1 port=$2 h
  h=$(local_health "$port")
  if [ -n "$h" ]; then
    if [ "${h%% *}" != "$voice" ]; then
      say "ERROR: port $port already serves voice '${h%% *}', not '$voice'. Use another PORT."
      return 1
    fi
    say "Agent server already up on :$port (voice $voice)."
    return 0
  fi
  say "Starting agent server: VOICE=$voice PORT=$port"
  (cd "$ROOT" && VOICE=$voice PORT=$port nohup uv run python -m app.server \
    > "$STATE_DIR/server-$port.log" 2>&1 &
   echo $! > "$STATE_DIR/server-$port.pid")
  for _ in $(seq 1 60); do
    h=$(local_health "$port")
    [ -n "$h" ] && { say "Agent server up on :$port."; return 0; }
    sleep 1
  done
  say "ERROR: agent server did not come up; see $STATE_DIR/server-$port.log"
  return 1
}

cmd_up() {
  local voice=${1:-} port=${2:-7860} pid host log
  require_voice "$voice" up || return 2
  pid=$(state_get TUNNEL_PID)
  if alive "$pid"; then
    say "Already connected: wss://$(state_get HOST)/ws (voice $(state_get VOICE), port $(state_get PORT))."
    return 0
  fi
  : > "$STATE"
  ensure_server "$voice" "$port" || return 1

  log="$STATE_DIR/tunnel.log"
  if [ -n "${NGROK_DOMAIN:-}" ] && command -v ngrok >/dev/null 2>&1; then
    host=$NGROK_DOMAIN
    nohup ngrok http --url="$host" "$port" --log=stdout > "$log" 2>&1 &
    pid=$!
  elif command -v cloudflared >/dev/null 2>&1; then
    nohup cloudflared tunnel --url "http://localhost:$port" > "$log" 2>&1 &
    pid=$!
    host=""
    for _ in $(seq 1 45); do
      host=$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$log" | head -1 | sed 's#https://##')
      [ -n "$host" ] && break
      sleep 1
    done
  else
    say "ERROR: no tunnel tool. brew install cloudflared (or ngrok + NGROK_DOMAIN)."
    return 1
  fi
  if [ -z "$host" ]; then
    say "ERROR: tunnel gave no address; see $log"; kill "$pid" 2>/dev/null; return 1
  fi
  { echo "TUNNEL_PID=$pid"; echo "HOST=$host"; echo "PORT=$port"; echo "VOICE=$voice"; } >> "$STATE"

  say "Waiting until Prosper can reach wss://$host/ws …"
  local deadline=$(( $(date +%s) + 120 ))
  while [ "$(date +%s)" -lt "$deadline" ]; do
    if [ "$(public_health_code "$host")" = "200" ] && public_ws_ok "$host"; then
      event "UP wss://$host/ws voice=$voice port=$port"
      say "CONNECTED: wss://$host/ws  (voice $voice → :$port)"
      if [ -z "${NGROK_DOMAIN:-}" ]; then
        say "NEW ADDRESS: save it in dashboard Settings → Integration BEFORE pressing Call / Run all."
      fi
      return 0
    fi
    sleep 2
  done
  say "ERROR: not publicly reachable after 2 min; disconnecting. See $log"
  cmd_down >/dev/null
  return 1
}

cmd_down() {
  local all=${1:-} pid host port code
  pid=$(state_get TUNNEL_PID); host=$(state_get HOST)
  if alive "$pid"; then
    kill "$pid" 2>/dev/null
    for _ in $(seq 1 10); do alive "$pid" || break; sleep 1; done
    alive "$pid" && kill -9 "$pid" 2>/dev/null
    say "Tunnel closed (pid $pid)."
  else
    say "No tunnel of ours was running."
  fi
  if [ "$all" = "--all" ]; then
    other_tunnels | while read -r opid _; do kill "$opid" 2>/dev/null && say "Closed other tunnel pid $opid"; done
    for f in "$STATE_DIR"/server-*.pid; do  # only servers this helper started
      [ -f "$f" ] || continue
      port=$(basename "$f" .pid); port=${port#server-}
      lsof -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null | while read -r spid; do kill "$spid" 2>/dev/null; done
      kill "$(cat "$f")" 2>/dev/null
      rm -f "$f"
      say "Stopped the agent server this helper started on :$port."
    done
  elif [ -n "$(other_tunnels)" ]; then
    say "WARNING: other tunnels are still running (down --all closes them):"
    other_tunnels
  fi
  if [ -n "$host" ]; then
    code=$(public_health_code "$host")
    if [ "$code" = "200" ]; then
      say "WARNING: https://$host still answers 200. Check 'status'."
    else
      say "DISCONNECTED: wss://$host/ws no longer answers (HTTP $code)."
    fi
  fi
  event "DOWN host=${host:-none}"
  : > "$STATE"
}

cmd_status() {
  local pid host port h
  pid=$(state_get TUNNEL_PID); host=$(state_get HOST); port=$(state_get PORT)
  if alive "$pid"; then
    h=$(local_health "$port")
    say "CONNECTED via pid $pid: wss://$host/ws → :$port (local health: ${h:-DOWN}; public /health HTTP $(public_health_code "$host"))"
  else
    say "DISCONNECTED (no tunnel of ours)."
  fi
  if [ -n "$(other_tunnels)" ]; then
    say "Tunnel processes on this machine:"; other_tunnels
  fi
  [ -f "$EVENTS" ] && tail -3 "$EVENTS" | sed 's/^/  last: /'
  return 0
}

cmd_session() {
  local voice=${1:-} port=${2:-7860}
  local idle=${IDLE_SECS:-90} first=${FIRST_CALL_SECS:-900} max=${MAX_SECS:-5400}
  local start now last_active=0 seen=0 h active
  require_voice "$voice" session || exit 2
  trap 'echo; trap - EXIT; cmd_down; exit 0' INT TERM
  trap 'cmd_down' EXIT
  cmd_up "$voice" "$port" || exit 1
  say "Session open. Start the run now (Call / Run all). I disconnect after ${idle}s with no active call."
  start=$(date +%s)
  while :; do
    now=$(date +%s)
    h=$(local_health "$port"); active=${h##* }
    [ -z "$h" ] && { say "Agent server stopped answering; ending session."; break; }
    if [ "${active:-0}" -gt 0 ]; then
      [ $seen -eq 0 ] && say "First call arrived."
      seen=1; last_active=$now
    fi
    if [ $seen -eq 0 ] && [ $((now - start)) -ge "$first" ]; then
      say "No call within ${first}s; ending session."; break
    fi
    if [ $seen -eq 1 ] && [ "${active:-0}" -eq 0 ] && [ $((now - last_active)) -ge "$idle" ]; then
      say "No active call for ${idle}s; run looks finished."; break
    fi
    if [ $((now - start)) -ge "$max" ]; then say "Hit MAX_SECS=${max}; ending session."; break; fi
    sleep 5
  done
}

case "${1:-status}" in
  up) shift; cmd_up "$@" ;;
  down) shift; cmd_down "$@" ;;
  status) cmd_status ;;
  session) shift; cmd_session "$@" ;;
  *) sed -n '2,20p' "$0"; exit 2 ;;
esac
