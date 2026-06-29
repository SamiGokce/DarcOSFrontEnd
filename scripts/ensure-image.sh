#!/usr/bin/env bash
# Source from kernel repo dev.sh: ensure platform image exists (pull Docker Hub, else local build).
set -euo pipefail

PLATFORM_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${DARCYOS_IMAGE:-codejedi-ai/cs452rotos-platform:latest}"

ensure_platform_image() {
	if docker image inspect "${IMAGE}" >/dev/null 2>&1; then
		return 0
	fi
	echo "Pulling ${IMAGE} from Docker Hub..."
	if docker pull "${IMAGE}"; then
		return 0
	fi
	echo "Docker Hub pull failed — building locally from CS452ROTOS-PLATFORM..."
	bash "${PLATFORM_ROOT}/build.sh"
	if [ "${IMAGE}" != "darcyos-dev" ] && [ "${IMAGE}" != "darcyos-dev:latest" ]; then
		local arch
		case "$(uname -m)" in
			x86_64 | amd64) arch=amd64 ;;
			aarch64 | arm64) arch=arm64 ;;
			*) arch=amd64 ;;
		esac
		docker tag "darcyos-dev:${arch}" "${IMAGE}" 2>/dev/null \
			|| docker tag darcyos-dev "${IMAGE}" 2>/dev/null \
			|| true
	fi
}

ensure_platform_image
