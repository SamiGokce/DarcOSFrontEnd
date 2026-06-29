#!/usr/bin/env bash
# Dev wrapper — mounts this kernel repo into the CS452ROTOS-PLATFORM container.
# Terminal-only on the host TTY. Browser / ttyd remote dev is PLATFORM-only
# (see CS452ROTOS-PLATFORM README); OS repos never start ttyd.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM_DEFAULT="${ROOT}/../github_codejedi-ai_CS452ROTOS-PLATFORM"
if [ -d "${PLATFORM_DEFAULT}" ]; then
	PLATFORM="$(cd "${PLATFORM_DEFAULT}" && pwd)"
else
	PLATFORM="${PLATFORM:-}"
fi
cd "$ROOT"

DC=(docker compose)

usage() {
	cat <<'EOF'
Usage: ./dev.sh <command>

Commands:
  build-image Pull/build the shared platform image (Docker Hub or local PLATFORM)
  run         Build kernel and run in QEMU — host terminal (Ctrl+A X to exit)
  test        CI smoke test (timed QEMU boot)
  test-k1     Run K1 tests under QEMU
  test-k2     Run K2 tests under QEMU
  test-k3     Run K3 tests under QEMU
  test-k4     Run K4 tests under QEMU
  shell       Open a shell in the dev container
  make [args] Run make inside the container (default: make all)

Environment:
  DARCYOS_IMAGE   default: codejedi-ai/cs452rotos-platform:latest
  PLATFORM        override path to CS452ROTOS-PLATFORM checkout (optional)
EOF
}

ensure_image() {
	DARCYOS_IMAGE="${DARCYOS_IMAGE:-codejedi-ai/cs452rotos-platform:latest}"
	if [ -n "${PLATFORM}" ] && [ -f "${PLATFORM}/scripts/ensure-image.sh" ]; then
		# shellcheck source=/dev/null
		source "${PLATFORM}/scripts/ensure-image.sh"
		return 0
	fi
	if docker image inspect "${DARCYOS_IMAGE}" >/dev/null 2>&1; then
		return 0
	fi
	echo "Pulling ${DARCYOS_IMAGE} from Docker Hub..."
	docker pull "${DARCYOS_IMAGE}"
}

kvm_args() {
	if [ -e /dev/kvm ]; then
		echo --device /dev/kvm
		if command -v getent >/dev/null 2>&1 && getent group kvm >/dev/null 2>&1; then
			echo --group-add "$(getent group kvm | cut -d: -f3)"
		fi
	fi
}

compose_run() {
	local service="$1"
	shift
	local -a tty=(-i)
	if [ -t 0 ] && [ -t 1 ]; then
		tty=(-it)
	fi
	# shellcheck disable=SC2207
	local -a kvm=( $(kvm_args) )
	"${DC[@]}" run --rm "${tty[@]}" "${kvm[@]}" "$service" "$@"
}

cmd="${1:-run}"
shift || true

case "${cmd}" in
	build|build-image)
		ensure_image
		;;
	run)
		ensure_image
		compose_run run
		;;
	test)
		ensure_image
		"${DC[@]}" run --rm -T $(kvm_args) test
		;;
	test-k1|test-k2|test-k3|test-k4)
		ensure_image
		"${DC[@]}" run --rm -T $(kvm_args) shell "${cmd}"
		;;
	shell|bash)
		ensure_image
		compose_run shell
		;;
	make)
		ensure_image
		if [ "$#" -eq 0 ]; then
			"${DC[@]}" run --rm -T $(kvm_args) build
		else
			"${DC[@]}" run --rm -T $(kvm_args) shell make "$@"
		fi
		;;
	help|-h|--help)
		usage
		;;
	*)
		echo "Unknown command: ${cmd}" >&2
		usage >&2
		exit 1
		;;
esac
