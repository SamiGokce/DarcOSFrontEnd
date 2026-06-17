#!/usr/bin/env bash
#
# Build DarcOS ISO inside an Arch Linux container (for Fedora, Ubuntu, etc.)
#

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROFILE="${ROOT}/profiles/darcos"
OUT="${ROOT}/out"
WORK="${ROOT}/work"
IMAGE="${DARCOS_BUILD_IMAGE:-archlinux/archlinux:latest}"
# Persistent pacman package cache so rebuilds don't re-download ~1.4 GB.
PKGCACHE="${DARCOS_PKG_CACHE:-${ROOT}/.pkgcache}"
SKIP_MARKER="${PROFILE}/airootfs/etc/darcos/skip-hermes-install"

usage() {
    cat <<EOF
Usage: $(basename "$0") [OPTIONS]

Build the DarcOS ISO using archiso inside an Arch Linux container.
Use this on Fedora, Ubuntu, or any non-Arch host with Docker/Podman.

Options:
  -c, --clean       Remove work/ and out/ before building
      --skip-hermes Skip Hermes Agent download during ISO build
  -h, --help        Show this help

Environment:
  DARCOS_BUILD_IMAGE   Container image (default: archlinux/archlinux:latest)
  CONTAINER_RUNTIME    Force 'docker' or 'podman'
EOF
}

detect_runtime() {
    if [[ -n "${CONTAINER_RUNTIME:-}" ]]; then
        command -v "${CONTAINER_RUNTIME}" &>/dev/null || {
            echo "CONTAINER_RUNTIME=${CONTAINER_RUNTIME} not found." >&2
            exit 1
        }
        echo "${CONTAINER_RUNTIME}"
        return
    fi
    if command -v podman &>/dev/null; then
        echo podman
    elif command -v docker &>/dev/null; then
        echo docker
    else
        echo "Neither podman nor docker found. Install one to build on non-Arch hosts." >&2
        exit 1
    fi
}

clean_artifacts() {
    local runtime="$1"
    echo "Cleaning ${WORK} and ${OUT}..."
    # A previous privileged build leaves root-owned files the host user can't
    # delete. Fall back to removing them inside the container (runs as root).
    if ! rm -rf "${WORK}" "${OUT}" 2>/dev/null; then
        echo "Root-owned artifacts from a previous build — removing via ${runtime}..."
        "${runtime}" run --rm \
            --security-opt label=disable \
            -v "${ROOT}:/build" -w /build \
            "${IMAGE}" rm -rf work out \
            || { echo "Cleanup failed. As a last resort run: sudo rm -rf work out" >&2; exit 1; }
    fi
}

main() {
    local do_clean=false
    local skip_hermes=false
    local runtime

    while [[ $# -gt 0 ]]; do
        case "$1" in
            -c|--clean) do_clean=true; shift ;;
            --skip-hermes) skip_hermes=true; shift ;;
            -h|--help) usage; exit 0 ;;
            *) echo "Unknown option: $1" >&2; usage; exit 1 ;;
        esac
    done

    runtime="$(detect_runtime)"
    [[ "${do_clean}" == true ]] && clean_artifacts "${runtime}"

    mkdir -p "${OUT}" "${WORK}" "${PKGCACHE}"

    if [[ "${skip_hermes}" == true ]]; then
        echo "Hermes install will be skipped for this build."
        touch "${SKIP_MARKER}"
        trap 'rm -f "${SKIP_MARKER}"' EXIT
    fi

    echo "Building DarcOS ISO via ${runtime} (${IMAGE})..."
    echo "Repo mounted at /build — output will be in ${OUT}/"
    echo "Note: first build downloads ~1 GB of Arch packages (10-30 min, sparse progress)."
    echo

    # mkarchiso itself requires root (loop mounts, pacstrap, squashfs), so the
    # build runs as root inside the container — but we hand ownership of the
    # artifacts back to the invoking host user so nothing lands as root on the
    # host. HOST_UID/HOST_GID are consumed by the trailing chown.
    if ! "${runtime}" run --rm -i \
        --privileged \
        --cap-add SYS_ADMIN \
        --security-opt label=disable \
        -e HOST_UID="$(id -u)" \
        -e HOST_GID="$(id -g)" \
        -v "${ROOT}:/build" \
        -v "${PKGCACHE}:/var/cache/pacman/pkg" \
        -w /build \
        "${IMAGE}" \
        bash -lc 'set -euo pipefail
cleanup_owner() { chown -R "${HOST_UID}:${HOST_GID}" work out 2>/dev/null || true; }
trap cleanup_owner EXIT
pacman -Sy --needed --noconfirm archiso git curl rsync
# Auto-answer pacman provider/menu prompts during mkarchiso (e.g. jack2 vs
# pipewire-jack). Use process substitution, not a pipe: a `yes |` pipe gets
# SIGPIPE when build.sh finishes, which pipefail would report as a false failure.
bash scripts/build.sh < <(yes "")'; then
        cat >&2 <<EOF

Container run failed. Common fixes on Fedora:
  sudo usermod -aG docker "$USER"   # then log out and back in
  newgrp docker                     # or start a new shell in the group
  sudo bash scripts/build-container.sh $@

Or install Podman (rootless, no daemon):
  sudo dnf install podman
  CONTAINER_RUNTIME=podman bash scripts/build-container.sh
EOF
        exit 1
    fi

    echo
    echo "Container build finished. ISO(s):"
    ls -lh "${OUT}"/*.iso 2>/dev/null || ls -lh "${OUT}/"
}

main "$@"
