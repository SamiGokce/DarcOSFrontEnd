#!/usr/bin/env bash
# Validates DarcOS archiso profile structure (no root, no network required).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PROFILE="${ROOT}/profiles/darcos"
errors=0

fail() {
    echo "FAIL: $1" >&2
    errors=$((errors + 1))
}

require_file() {
    local path="$1"
    if [[ ! -f "${PROFILE}/${path}" ]]; then
        fail "missing file: profiles/darcos/${path}"
    fi
}

require_executable() {
    local path="$1"
    require_file "${path}"
    if [[ ! -x "${PROFILE}/${path}" ]]; then
        fail "not executable: profiles/darcos/${path}"
    fi
}

echo "Validating DarcOS profile at ${PROFILE}..."

require_file "profiledef.sh"
require_file "pacman.conf"
require_file "packages.x86_64"
require_file "bootstrap_packages"
require_file "airootfs/etc/darcos-release"
require_file "airootfs/etc/hostname"
require_file "airootfs/usr/local/bin/darcos-install"
require_executable "airootfs/usr/local/bin/darcos"
require_executable "airootfs/usr/local/bin/darcos-install"
require_executable "airootfs/usr/local/bin/darcos-ai"
require_executable "airootfs/usr/local/lib/darcos/install-hermes.sh"
require_executable "airootfs/root/.automated_script.sh"
require_file "airootfs/etc/profile.d/darcos-hermes.sh"
require_file "airootfs/etc/darcos/hermes.conf"

# profiledef.sh must define iso_name
if ! grep -q 'iso_name="darcos"' "${PROFILE}/profiledef.sh"; then
    fail 'profiledef.sh must set iso_name="darcos"'
fi

# packages must include base and linux
for pkg in base linux archinstall ripgrep ffmpeg; do
    if ! grep -qx "${pkg}" "${PROFILE}/packages.x86_64"; then
        fail "packages.x86_64 missing required package: ${pkg}"
    fi
done

if ! grep -q 'DARCOS_DEFAULT_AI="hermes"' "${PROFILE}/airootfs/etc/darcos-release"; then
    fail 'darcos-release must set DARCOS_DEFAULT_AI="hermes"'
fi

if ! grep -q 'install-hermes.sh' "${PROFILE}/airootfs/root/.automated_script.sh"; then
    fail 'automated_script.sh must invoke install-hermes.sh'
fi

if ! grep -q 'darcos setup' "${PROFILE}/airootfs/etc/motd"; then
    fail 'motd must reference darcos setup'
fi

if [[ "${errors}" -gt 0 ]]; then
    echo "${errors} validation error(s)." >&2
    exit 1
fi

echo "Profile validation passed."
