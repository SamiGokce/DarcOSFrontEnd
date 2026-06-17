#!/usr/bin/env bash
#
# DarcOS OS1 boot experience — plays the "Her" boot chime and shows the
# 3D helix that resolves into a circle, themed to the active color mode.
#
# Designed to FAIL SAFE: if no GPU / compositor / browser is available it
# logs and exits 0 so it can never block or break the boot.
#

set -uo pipefail

readonly HELIX="file:///usr/share/darcos/boot-helix/index.html"
readonly SOUND="/usr/share/darcos/sounds/os1-boot.wav"
readonly SPLASH_SECONDS="${DARCOS_SPLASH_SECONDS:-7}"
readonly LOG_PREFIX="[darcos-splash]"
log() { echo "${LOG_PREFIX} $*"; }

# Honor an opt-out.
[[ -f /etc/darcos/skip-splash ]] && { log "skip marker present; skipping."; exit 0; }

theme="warm"
[[ -f /etc/darcos/theme ]] && theme="$(cat /etc/darcos/theme)"
url="${HELIX}?theme=${theme}"

# Start the HONEST progress writer — the helix tracks real boot, and completes
# the circle the instant the agent daemon's socket appears (agent online).
[[ -x /usr/local/lib/darcos/boot-progress.sh ]] && \
    /usr/local/lib/darcos/boot-progress.sh &

# ── boot chime (best effort, backgrounded) ─────────────────────────────────
play_sound() {
    [[ -f "${SOUND}" ]] || return 0
    if   command -v paplay &>/dev/null; then paplay "${SOUND}"
    elif command -v aplay  &>/dev/null; then aplay -q "${SOUND}"
    elif command -v ffplay &>/dev/null; then ffplay -nodisp -autoexit -loglevel quiet "${SOUND}"
    fi
}
play_sound &

# ── pick a WebGL-capable kiosk browser ─────────────────────────────────────
browser_cmd=()
if   command -v cog &>/dev/null; then
    browser_cmd=(cog "${url}")
elif command -v chromium &>/dev/null; then
    browser_cmd=(chromium --kiosk --no-first-run --noerrdialogs
                 --allow-file-access-from-files
                 --enable-features=UseOzonePlatform --ozone-platform=wayland "${url}")
elif command -v firefox &>/dev/null; then
    browser_cmd=(firefox --kiosk "${url}")
else
    log "no kiosk browser (cog/chromium/firefox); playing chime only."
    wait; exit 0
fi

# ── show it ────────────────────────────────────────────────────────────────
# Already inside a Wayland/X session → just run the browser fullscreen.
if [[ -n "${WAYLAND_DISPLAY:-}" || -n "${DISPLAY:-}" ]]; then
    timeout "${SPLASH_SECONDS}" "${browser_cmd[@]}" >/dev/null 2>&1
    exit 0
fi

# Otherwise bring up a minimal compositor (cage) just for the splash.
if command -v cage &>/dev/null; then
    timeout "${SPLASH_SECONDS}" cage -- "${browser_cmd[@]}" >/dev/null 2>&1
else
    log "no compositor (cage) and no active session; playing chime only."
fi

wait 2>/dev/null
exit 0
