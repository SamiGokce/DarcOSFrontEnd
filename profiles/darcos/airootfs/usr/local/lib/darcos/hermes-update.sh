#!/usr/bin/env bash
#
# DarcOS — auto-update Hermes Agent to the latest release.
# Run by the darcos-hermes-update.timer (daily) or manually via `darcos update`.
#

set -euo pipefail

readonly LOG_PREFIX="[darcos-hermes-update]"
log()  { echo "${LOG_PREFIX} $*"; }
warn() { echo "${LOG_PREFIX} WARNING: $*" >&2; }

# Load DarcOS Hermes settings (HERMES_INSTALL_URL, etc.) if present.
# shellcheck source=/dev/null
[[ -f /etc/darcos/hermes.conf ]] && source /etc/darcos/hermes.conf

readonly HERMES_INSTALL_URL="${HERMES_INSTALL_URL:-https://hermes-agent.nousresearch.com/install.sh}"

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        echo "${LOG_PREFIX} must run as root." >&2
        exit 1
    fi
}

update_disabled() {
    [[ -f /etc/darcos/skip-hermes-update ]] || [[ "${DARCOS_SKIP_HERMES_UPDATE:-0}" == "1" ]]
}

hermes_version() {
    command -v hermes &>/dev/null && hermes --version 2>/dev/null || true
}

main() {
    require_root

    if update_disabled; then
        log "Auto-update disabled (skip marker or DARCOS_SKIP_HERMES_UPDATE=1)."
        exit 0
    fi

    # Best-effort network check — stay quiet and succeed when offline so the
    # timer doesn't spam failures on a disconnected live session.
    if ! curl -fsS --head "${HERMES_INSTALL_URL}" >/dev/null 2>&1; then
        log "Installer unreachable (offline?); skipping update."
        exit 0
    fi

    local before after installer
    before="$(hermes_version)"

    installer="$(mktemp)"
    trap 'rm -f "${installer}"' EXIT

    log "Fetching latest Hermes Agent installer..."
    if ! curl -fsSL "${HERMES_INSTALL_URL}" -o "${installer}"; then
        warn "download failed; keeping current version ${before:-none}."
        exit 0
    fi

    log "Applying update (non-interactive)..."
    if ! bash "${installer}" --non-interactive --skip-setup --skip-browser; then
        warn "installer exited non-zero; current version ${before:-none} left in place."
        exit 1
    fi

    after="$(hermes_version)"
    if [[ "${before}" != "${after}" ]]; then
        log "Hermes updated: ${before:-none} -> ${after:-unknown}"
    else
        log "Hermes already up to date (${after:-unknown})."
    fi
}

main "$@"
