#!/usr/bin/env bash
#
# DarcOS welcome / recovery hub launcher — the macOS-Utilities-style landing
# screen the system shows after the boot helix. From here you Install, Repair,
# open Disk Utility, or Try DarcOS in RAM — with the agent always at the ready.
#
# Fail-safe: if there's no GPU/compositor/browser it exits 0 (so boot is never
# blocked); the system then falls back to the text login + `darcos` CLI.
#

set -uo pipefail

readonly HUB="file:///usr/share/darcos/welcome/index.html"
log() { echo "[darcos-welcome] $*"; }

[[ -f /etc/darcos/skip-welcome ]] && { log "skip marker; not showing hub."; exit 0; }

theme="warm"; [[ -f /etc/darcos/theme ]] && theme="$(cat /etc/darcos/theme)"
url="${HUB}?theme=${theme}"

browser=()
if   command -v cog &>/dev/null;      then browser=(cog "${url}")
elif command -v chromium &>/dev/null; then
    browser=(chromium --kiosk --no-first-run --noerrdialogs
             --allow-file-access-from-files --ozone-platform=wayland "${url}")
elif command -v firefox &>/dev/null;  then browser=(firefox --kiosk "${url}")
else log "no kiosk browser; falling back to text login."; exit 0
fi

# Inside a session already → run directly. Otherwise bring up cage just for this.
if [[ -n "${WAYLAND_DISPLAY:-}${DISPLAY:-}" ]]; then
    exec "${browser[@]}"
elif command -v cage &>/dev/null; then
    exec cage -- "${browser[@]}"
else
    log "no compositor; welcome hub unavailable — text login instead."
    exit 0
fi
