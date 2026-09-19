#!/usr/bin/env bash
# Install the endpoint traffic light in the macOS menu bar (SwiftBar plugin).
#   scripts/menubar/install.sh
# 🔴 a tunnel is open (Prosper can reach us) · 🟡 local test calls only · 🟢 nothing running.
set -euo pipefail
PLUGIN="$(cd "$(dirname "$0")" && pwd)/prosper-endpoint.5s.sh"
DIR="$HOME/.swiftbar-plugins"

[ -d /Applications/SwiftBar.app ] || brew install --cask swiftbar
mkdir -p "$DIR"
chmod +x "$PLUGIN"
ln -sf "$PLUGIN" "$DIR/prosper-endpoint.5s.sh"
# Only point SwiftBar at our folder if it has none yet; otherwise just drop the link in its folder.
current=$(defaults read com.ameba.SwiftBar PluginDirectory 2>/dev/null || true)
if [ -z "$current" ]; then
  defaults write com.ameba.SwiftBar PluginDirectory "$DIR"
elif [ "$current" != "$DIR" ]; then
  ln -sf "$PLUGIN" "$current/prosper-endpoint.5s.sh"
  DIR=$current
fi
pkill -x SwiftBar 2>/dev/null || true
open -a SwiftBar
echo "Traffic light installed: $DIR/prosper-endpoint.5s.sh -> $PLUGIN (refreshes every 5 s)."
