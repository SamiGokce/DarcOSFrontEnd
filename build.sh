#!/usr/bin/env bash
# Build the shared darcyos-dev image (QEMU 9.2.3 + toolchain 15.2).
# Supports linux/amd64 (x64) and linux/arm64 (ARM) host platforms.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE="${DARCYOS_IMAGE:-darcyos-dev}"
BUILDER="${DARCYOS_BUILDX_BUILDER:-darcyos-platform}"

usage() {
	cat <<'EOF'
Usage: ./build.sh [options]

Build the CS452ROTOS-PLATFORM dev image for the host CPU architecture(s).

Options:
  --all           Build both linux/amd64 and linux/arm64 images
                  (tags: IMAGE:amd64 and IMAGE:arm64; IMAGE -> native arch)
  --platform P    Build for one platform (linux/amd64 or linux/arm64)
  -h, --help      Show this help

Environment:
  DARCYOS_IMAGE           Image name (default: darcyos-dev)
  DARCYOS_PLATFORMS       Comma-separated platforms (e.g. linux/amd64,linux/arm64)
  DARCYOS_BUILDX_BUILDER  buildx builder name (default: darcyos-platform)

Without options, builds for the current machine only.
EOF
}

native_platform() {
	case "$(uname -m)" in
		x86_64 | amd64) echo linux/amd64 ;;
		aarch64 | arm64) echo linux/arm64 ;;
		*)
			echo "Unsupported host architecture: $(uname -m)" >&2
			exit 1
			;;
	esac
}

platform_tag() {
	case "$1" in
		linux/amd64) echo amd64 ;;
		linux/arm64) echo arm64 ;;
		*)
			echo "Unsupported platform: $1" >&2
			exit 1
			;;
	esac
}

ensure_deps() {
	if [ ! -f "${ROOT}/deps/qemu-9.2.3.tar.xz" ]; then
		echo "Missing deps/qemu-9.2.3.tar.xz in PLATFORM repo." >&2
		echo "Run: git lfs pull" >&2
		exit 1
	fi
	for host in x86_64 aarch64; do
		if ! ls "${ROOT}/deps"/arm-gnu-toolchain-15.2.rel1-"${host}"-aarch64-none-elf.tar.xz >/dev/null 2>&1; then
			echo "Missing ARM toolchain tarball for host ${host} in ${ROOT}/deps/" >&2
			exit 1
		fi
	done
}

ensure_buildx() {
	if ! docker buildx inspect "${BUILDER}" >/dev/null 2>&1; then
		docker buildx create --name "${BUILDER}" --use --bootstrap >/dev/null
	else
		docker buildx use "${BUILDER}" >/dev/null
	fi
}

build_one() {
	local platform="$1"
	local arch
	arch="$(platform_tag "${platform}")"
	echo "Building ${IMAGE}:${arch} for ${platform}..."
	docker buildx build \
		--platform "${platform}" \
		-t "${IMAGE}:${arch}" \
		--load \
		"${ROOT}"
}

BUILD_ALL=false
REQUESTED_PLATFORM=""

while [ $# -gt 0 ]; do
	case "$1" in
		--all)
			BUILD_ALL=true
			;;
		--platform)
			shift
			REQUESTED_PLATFORM="${1:?--platform requires a value}"
			;;
		-h | --help)
			usage
			exit 0
			;;
		*)
			echo "Unknown option: $1" >&2
			usage >&2
			exit 1
			;;
	esac
	shift
done

ensure_deps
ensure_buildx

NATIVE="$(native_platform)"

if [ -n "${DARCYOS_PLATFORMS:-}" ]; then
	IFS=',' read -r -a PLATFORMS <<< "${DARCYOS_PLATFORMS}"
elif [ "${BUILD_ALL}" = true ]; then
	PLATFORMS=(linux/amd64 linux/arm64)
elif [ -n "${REQUESTED_PLATFORM}" ]; then
	PLATFORMS=("${REQUESTED_PLATFORM}")
else
	PLATFORMS=("${NATIVE}")
fi

for platform in "${PLATFORMS[@]}"; do
	build_one "${platform}"
done

native_arch="$(platform_tag "${NATIVE}")"
docker tag "${IMAGE}:${native_arch}" "${IMAGE}"
echo "Done. Default tag ${IMAGE} -> ${IMAGE}:${native_arch}"
if [ "${#PLATFORMS[@]}" -gt 1 ]; then
	echo "Per-arch tags: ${IMAGE}:amd64, ${IMAGE}:arm64"
fi
echo "Use DARCYOS_IMAGE=${IMAGE} ./dev.sh run from any kernel repo."
