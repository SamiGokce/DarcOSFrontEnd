#!/usr/bin/env bash
#
# Install Hermes Agent system-wide for DarcOS ISO / installed systems.
# Invoked as root during archiso build (.automated_script.sh) or manually.
#

set -euo pipefail

readonly HERMES_INSTALL_URL="${HERMES_INSTALL_URL:-https://hermes-agent.nousresearch.com/install.sh}"
readonly HERMES_SEED_DIR="/etc/darcos/hermes-seed"
readonly LOG_PREFIX="[darcos-hermes]"

log() { echo "${LOG_PREFIX} $*"; }
warn() { echo "${LOG_PREFIX} WARNING: $*" >&2; }

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        echo "${LOG_PREFIX} must run as root." >&2
        exit 1
    fi
}

skip_install() {
    [[ -f /etc/darcos/skip-hermes-install ]] || [[ "${DARCOS_SKIP_HERMES:-0}" == "1" ]]
}

download_installer() {
    local dest="$1"
    if ! curl -fsSL "${HERMES_INSTALL_URL}" -o "${dest}"; then
        warn "failed to download installer from ${HERMES_INSTALL_URL}"
        return 1
    fi
}

install_hermes() {
    local installer
    installer="$(mktemp)"
    trap 'rm -f "${installer}"' RETURN

    log "Downloading Hermes Agent installer..."
    download_installer "${installer}" || return 1

    # Root on Linux → FHS layout:
    #   /usr/local/lib/hermes-agent  /usr/local/bin/hermes  /root/.hermes
    log "Installing Hermes Agent (non-interactive, no browser bundle)..."
    bash "${installer}" \
        --non-interactive \
        --skip-setup \
        --skip-browser
}

seed_user_config() {
    local source_home="${HERMES_HOME:-/root/.hermes}"

    if [[ ! -d "${source_home}" ]]; then
        warn "Hermes data directory missing at ${source_home}; skipping seed"
        return 0
    fi

    log "Seeding default Hermes config at ${HERMES_SEED_DIR}..."
    mkdir -p "${HERMES_SEED_DIR}"
    rsync -a --delete \
        --exclude 'sessions/' \
        --exclude 'logs/' \
        --exclude 'pairing/' \
        --exclude 'image_cache/' \
        --exclude 'audio_cache/' \
        --exclude 'memories/' \
        --exclude 'cron/' \
        "${source_home}/" "${HERMES_SEED_DIR}/"

    chmod -R go-rwx "${HERMES_SEED_DIR}" 2>/dev/null || true
    [[ -f "${HERMES_SEED_DIR}/.env" ]] && chmod 600 "${HERMES_SEED_DIR}/.env"
}

verify_install() {
    if command -v hermes &>/dev/null; then
        log "Hermes ready: $(command -v hermes)"
        return 0
    fi
    warn "hermes command not found after install"
    return 1
}

main() {
    require_root

    if skip_install; then
        log "Skipping Hermes install (skip marker or DARCOS_SKIP_HERMES=1)"
        exit 0
    fi

    if install_hermes && verify_install; then
        seed_user_config
        log "Hermes Agent installed successfully."
        exit 0
    fi

    warn "Hermes install failed; ISO will build without a pre-installed agent."
    exit 1
}

main "$@"
