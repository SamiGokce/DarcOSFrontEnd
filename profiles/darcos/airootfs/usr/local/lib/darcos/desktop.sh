#!/usr/bin/env bash
#
# DarcOS desktop launcher — the Windows-12-style webtop (centered taskbar,
# Start, acrylic windows) with the agent built into the taskbar. Rendered in a
# kiosk browser, themed to the active color mode. Fail-safe: exits 0 if there's
# no GPU/compositor/browser so boot/login is never blocked.
#

set -uo pipefail

readonly PORT="${DARCOS_BRIDGE_PORT:-8787}"
log() { echo "[darcos-desktop] $*"; }

theme="warm"; [[ -f /etc/darcos/theme ]] && theme="$(cat /etc/darcos/theme)"

# On the live ISO, boot straight into the install/welcome hub on top of the desktop.
extra=""
grep -qa 'archisobasedir' /proc/cmdline 2>/dev/null && extra="&firstrun=1"

# Start the bridge so the desktop is REAL (talks to darcos-agentd: real files,
# real commands, real app launches). It serves the desktop over localhost.
if [[ -x /usr/local/lib/darcos/bridge.py ]] && ! curl -s "http://127.0.0.1:${PORT}/" -o /dev/null 2>&1; then
    DARCOS_BRIDGE_PORT="${PORT}" python3 /usr/local/lib/darcos/bridge.py &>/dev/null &
    sleep 1
fi
# Prefer the live bridge (real system); fall back to file:// (simulation) if down.
if curl -s "http://127.0.0.1:${PORT}/" -o /dev/null 2>&1; then
    url="http://127.0.0.1:${PORT}/index.html?theme=${theme}${extra}"
else
    url="file:///usr/share/darcos/desktop/index.html?theme=${theme}${extra}"
fi

browser=()
if   command -v cog &>/dev/null;      then browser=(cog "${url}")
elif command -v chromium &>/dev/null; then
    browser=(chromium --kiosk --no-first-run --noerrdialogs
             --allow-file-access-from-files --ozone-platform=wayland "${url}")
elif command -v firefox &>/dev/null;  then browser=(firefox --kiosk "${url}")
else log "no kiosk browser; desktop unavailable."; exit 0
fi

if [[ -n "${WAYLAND_DISPLAY:-}${DISPLAY:-}" ]]; then
    exec "${browser[@]}"
elif command -v cage &>/dev/null; then
    exec cage -- "${browser[@]}"
else
    log "no compositor; cannot start the desktop on this session."
    exit 0
fi
