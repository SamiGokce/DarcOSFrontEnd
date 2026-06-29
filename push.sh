#!/usr/bin/env bash
# Build multi-arch images and push to Docker Hub.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DOCKERHUB_REPO="${DOCKERHUB_REPO:-codejedi-ai/cs452rotos-platform}"
TAG="${DOCKERHUB_TAG:-latest}"
BUILDER="${DARCYOS_BUILDX_BUILDER:-darcyos-platform}"
PLATFORMS="${DARCYOS_PLATFORMS:-linux/amd64,linux/arm64}"

usage() {
	cat <<EOF
Usage: ./push.sh [options]

Build and push CS452ROTOS-PLATFORM to Docker Hub (multi-arch manifest).

Options:
  --dry-run       Print the buildx command without running it
  -h, --help      Show this help

Environment:
  DOCKERHUB_REPO          e.g. codejedi-ai/cs452rotos-platform (required for push)
  DOCKERHUB_TAG           default: latest
  DARCYOS_PLATFORMS       default: linux/amd64,linux/arm64
  DARCYOS_BUILDX_BUILDER  default: darcyos-platform

Log in first: docker login
EOF
}

DRY_RUN=false
while [ $# -gt 0 ]; do
	case "$1" in
		--dry-run) DRY_RUN=true ;;
		-h | --help) usage; exit 0 ;;
		*) echo "Unknown option: $1" >&2; usage >&2; exit 1 ;;
	esac
	shift
done

if [ -z "${DOCKERHUB_REPO}" ]; then
	echo "Set DOCKERHUB_REPO (e.g. codejedi-ai/cs452rotos-platform)" >&2
	exit 1
fi

if ! docker buildx inspect "${BUILDER}" >/dev/null 2>&1; then
	docker buildx create --name "${BUILDER}" --use --bootstrap >/dev/null
else
	docker buildx use "${BUILDER}" >/dev/null
fi

if [ ! -f "${ROOT}/deps/qemu-9.2.3.tar.xz" ]; then
	echo "Run: git lfs pull (in PLATFORM repo)" >&2
	exit 1
fi

REF="${DOCKERHUB_REPO}:${TAG}"
CMD=(
	docker buildx build
	--platform "${PLATFORMS}"
	-t "${REF}"
	--push
	"${ROOT}"
)

echo "Pushing ${REF} for ${PLATFORMS}..."
if [ "${DRY_RUN}" = true ]; then
	printf ' %q\n' "${CMD[@]}"
	exit 0
fi

"${CMD[@]}"
echo "Published ${REF}"
