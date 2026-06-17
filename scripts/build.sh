#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="${ROOT}/profiles/darcos"
OUT="${ROOT}/out"
WORK="${ROOT}/work"

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Build the DarcOS live ISO using archiso.

Options:
  -c, --clean       Remove work/ and out/ before building
      --skip-hermes Skip Hermes Agent download during ISO build
  -h, --help        Show this help
EOF
}

require_archiso() {
    if command -v mkarchiso &>/dev/null; then
        return 0
    fi

    if [[ -f /etc/os-release ]]; then
        # shellcheck source=/dev/null
        source /etc/os-release
        if [[ "${ID:-}" != "arch" && "${ID_LIKE:-}" != *"arch"* ]]; then
            cat >&2 <<EOF
mkarchiso not found. DarcOS ISO builds require archiso, which only runs on Arch Linux.

You are on: ${PRETTY_NAME:-unknown}

On Fedora / Ubuntu / other distros, use the container builder instead:
  make build-container

Or directly:
  bash scripts/build-container.sh
EOF
            exit 1
        fi
    fi

    echo "mkarchiso not found. Install archiso: sudo pacman -S archiso" >&2
    exit 1
}

require_root() {
    if [[ "${EUID}" -ne 0 ]]; then
        echo "ISO builds require root. Re-run with sudo." >&2
        exit 1
    fi
}

clean_artifacts() {
    echo "Cleaning ${WORK} and ${OUT}..."
    rm -rf "${WORK}" "${OUT}"
}

build_iso() {
    echo "Building DarcOS ISO from profile: ${PROFILE}"
    mkdir -p "${OUT}"
    mkarchiso -v -w "${WORK}" -o "${OUT}" "${PROFILE}"
    echo
    echo "Build complete. ISO(s) in: ${OUT}"
    ls -lh "${OUT}"/*.iso 2>/dev/null || ls -lh "${OUT}/"
}

main() {
    local do_clean=false
    local skip_hermes=false
    local skip_marker="${PROFILE}/airootfs/etc/darcos/skip-hermes-install"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -c|--clean) do_clean=true; shift ;;
            --skip-hermes) skip_hermes=true; shift ;;
            -h|--help) usage; exit 0 ;;
            *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
        esac
    done

    require_archiso
    require_root

    [[ "${do_clean}" == true ]] && clean_artifacts

    if [[ "${skip_hermes}" == true ]]; then
        echo "Hermes install will be skipped for this build."
        touch "${skip_marker}"
        trap 'rm -f "${skip_marker}"' EXIT
    fi

    build_iso
}

main "$@"
