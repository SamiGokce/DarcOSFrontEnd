#!/usr/bin/env bash
# Run Hermes install script from the DarcOS profile (requires root + network).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INSTALLER="${ROOT}/profiles/darcos/airootfs/usr/local/lib/darcos/install-hermes.sh"

if [[ ! -x "${INSTALLER}" ]]; then
    echo "Installer not found: ${INSTALLER}" >&2
    exit 1
fi

exec sudo bash "${INSTALLER}" "$@"
