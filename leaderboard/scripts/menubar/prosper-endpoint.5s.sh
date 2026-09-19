#!/bin/bash
# <xbar.title>Prosper endpoint</xbar.title>
# <xbar.desc>Red while any tunnel exposes our agent (Prosper can call it); green when fully disconnected.</xbar.desc>
# <swiftbar.hideAbout>true</swiftbar.hideAbout>
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
# <swiftbar.hideLastUpdated>true</swiftbar.hideLastUpdated>
# <swiftbar.hideDisablePlugin>true</swiftbar.hideDisablePlugin>
# <swiftbar.hideSwiftBar>true</swiftbar.hideSwiftBar>
#
# SwiftBar plugin (refreshes every 5 s, per the filename). Install: see "Endpoint policy" in AGENTS.md.
# Policy: we stay DISCONNECTED unless a run is in progress, so green is the normal state.
export PATH=/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin

REPO=$(cd "$(dirname "$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$0")")/../.." && pwd)
HELPER="$REPO/scripts/endpoint.sh"

# Only processes whose program IS cloudflared/ngrok (a shell whose command line mentions them is not a tunnel)
tunnels=$(ps -axo pid=,args= | awk '{n=split($2,a,"/"); b=a[n]; if ((b=="cloudflared" && $3=="tunnel") || (b=="ngrok" && ($3=="http" || $3=="start"))) print}')

# Every local agent server (anything answering /health with active_calls), and its live calls
servers=""
local_calls=0
for port in $(lsof -nP -iTCP -sTCP:LISTEN 2>/dev/null | awk '$1 ~ /^[Pp]ython/ {n=split($9,a,":"); print a[n]}' | sort -un); do
  h=$(curl -s -m 1 "http://localhost:$port/health" 2>/dev/null)
  case "$h" in *'"active_calls"'*) ;; *) continue ;; esac
  c=$(printf '%s' "$h" | grep -oE '"active_calls":[0-9]+' | cut -d: -f2)
  v=$(printf '%s' "$h" | grep -oE '"voice":"[a-z]+"' | cut -d'"' -f4)
  local_calls=$((local_calls + ${c:-0}))
  servers="$servers:$port ${v:-?} · live calls ${c:-0}"$'\n'
done

if [ -z "$tunnels" ]; then
  if [ "$local_calls" -gt 0 ]; then
    echo "🟡 $local_calls"
    echo "---"
    echo "Local test calls running: Prosper CANNOT reach us (no tunnel)"
  else
    echo "🟢"
    echo "---"
    echo "Endpoint DISCONNECTED: no tunnel, no calls"
  fi
  if [ -n "$servers" ]; then
    echo "Agent servers on this Mac"
    printf '%s' "$servers" | while read -r l; do [ -n "$l" ] && echo "--$l | font=Menlo size=11"; done
  fi
else
  total=0
  lines=""
  while read -r pid cmd; do
    [ -z "$pid" ] && continue
    case "$cmd" in
      *cloudflared*) port=$(printf '%s' "$cmd" | sed -n 's#.*localhost:\([0-9][0-9]*\).*#\1#p') ;;
      *) port=$(printf '%s' "$cmd" | grep -oE '(^| )[0-9]{2,5}( |$)' | tail -1 | tr -d ' ') ;;
    esac
    calls=$(curl -s -m 1 "http://localhost:${port:-0}/health" 2>/dev/null | grep -oE '"active_calls":[0-9]+' | cut -d: -f2)
    voice=$(curl -s -m 1 "http://localhost:${port:-0}/health" 2>/dev/null | grep -oE '"voice":"[a-z]+"' | cut -d'"' -f4)
    total=$((total + ${calls:-0}))
    lines="$lines${cmd%% *} → :${port:-?} (${voice:-no agent}) · live calls: ${calls:-?} · pid $pid"$'\n'
  done <<< "$tunnels"
  if [ "$total" -gt 0 ]; then echo "🔴 $total"; else echo "🔴"; fi
  echo "---"
  echo "Endpoint CONNECTED: Prosper can reach us | color=red"
  printf '%s' "$lines" | while read -r l; do [ -n "$l" ] && echo "$l | font=Menlo size=11"; done
  host=$(sed -n 's/^HOST=//p' "$REPO/logs/endpoint/state" 2>/dev/null | tail -1)
  [ -n "$host" ] && echo "wss://$host/ws | font=Menlo size=11"
  echo "---"
  echo "Disconnect everything | bash=$HELPER param1=down param2=--all terminal=false refresh=true"
fi
echo "---"
events="$REPO/logs/endpoint/events.log"
if [ -f "$events" ]; then
  echo "Recent"
  tail -4 "$events" | while read -r l; do echo "--$l | font=Menlo size=10"; done
fi
echo "Status in Terminal | bash=$HELPER param1=status terminal=true"
