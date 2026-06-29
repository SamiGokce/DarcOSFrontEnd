#!/usr/bin/env bash
# Copy canonical dev.sh / docker-compose.yml / CI workflow to all kernel repos.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLATFORM="$(cd "${SCRIPT_DIR}/.." && pwd)"
WORKSPACE="$(cd "${PLATFORM}/.." && pwd)"

render_compose() {
	local compose_name="$1"
	local variant="$2"
	local out="$3"

	local dev_cpus_line="" extra_volumes="" extra_env="" extra_block=""

	case "${variant}" in
	apu)
		dev_cpus_line='  cpus: "${DEV_CPUS:-1}"'
		extra_volumes=$'    - nix-disk:/disk\n'
		extra_env=$'    - DISK_ROOT=/disk\n'
		extra_block=$'\nvolumes:\n  nix-disk:'
		;;
	mekkana)
		extra_env=$'    - MARKLIN=${MARKLIN:-vhw}\n    - START_VHW=${START_VHW:-1}\n'
		;;
	smp|*)
		;;
	esac

	cat >"${out}" <<EOF
# Uses CS452ROTOS-PLATFORM from Docker Hub (see ../github_codejedi-ai_CS452ROTOS-PLATFORM)
#
# Terminal-only dev workflow — QEMU serial on host stdio.
# Browser / ttyd remote dev: CS452ROTOS-PLATFORM repo only (not kernel repos).
#
#   docker compose run --rm -it run      # interactive QEMU OS terminal (./dev.sh run)
#   docker compose run --rm -T build     # make all (./dev.sh make)
#   docker compose run --rm -T test      # timed smoke test (./dev.sh test)

name: ${compose_name}

x-dev: &dev
  image: \${DARCYOS_IMAGE:-codejedi-ai/cs452rotos-platform:latest}
  pull_policy: missing
${dev_cpus_line}
  volumes:
    - .:/workspace
${extra_volumes}  working_dir: /workspace
  environment:
    - XDIR=/opt/toolchain
    - IN_DOCKER=1
${extra_env}
services:
  build:
    <<: *dev
    entrypoint: ["bash", "/workspace/scripts/container-run.sh"]
    command: build

  test:
    <<: *dev
    entrypoint: ["bash", "/workspace/scripts/container-run.sh"]
    command: test

  run:
    <<: *dev
    stdin_open: true
    tty: true
    entrypoint: ["bash", "/workspace/scripts/container-run.sh"]
    command: run
${extra_block}
EOF
}

sync_repo() {
	local repo_dir="$1"
	local compose_name="$2"
	local variant="${3:-smp}"

	echo "==> ${repo_dir}"
	install -m 0755 "${SCRIPT_DIR}/os-dev.sh" "${repo_dir}/dev.sh"
	render_compose "${compose_name}" "${variant}" "${repo_dir}/docker-compose.yml"
	mkdir -p "${repo_dir}/.github/workflows"
	cp "${SCRIPT_DIR}/os-ci.yml" "${repo_dir}/.github/workflows/ci.yml"
}

sync_repo "${WORKSPACE}/github_codejedi-ai_CS452ROTOS-APU-DarcyOS" smpos-nix apu
sync_repo "${WORKSPACE}/github_codejedi-ai_CS452ROTOS-APU-KatarOS" smpos-nix apu
sync_repo "${WORKSPACE}/github_codejedi-ai_CS452ROTOS-APU-NyxOS" smpos-nix apu
sync_repo "${WORKSPACE}/github_codejedi-ai_CS452ROTOS-APU-AtariOS" smpos-nix apu
sync_repo "${WORKSPACE}/github_codejedi-ai_CS452ROTOS-SMP-DarcyOS" smp-darcyos smp
sync_repo "${WORKSPACE}/github_codejedi-ai_CS452ROTOS-SMP-IrisOS" irisos smp
sync_repo "${WORKSPACE}/github_codejedi-ai_CS452ROTOS-SMP-PrimeOS" primeos smp
sync_repo "${WORKSPACE}/github_codejedi-ai_CS452ROTOS-SMP-MekkanaOS" mekkanaos mekkana
sync_repo "${WORKSPACE}/uwaterloo_d273liu_CS452ROTOS-SMP-cs452-trains" cs452-trains smp

echo "Done — synced dev.sh, docker-compose.yml, and .github/workflows/ci.yml to 9 kernel repos."
