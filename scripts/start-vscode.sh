#!/usr/bin/env bash
# Serve VS Code in the browser; default folder is cs452's projects workbench.
set -euo pipefail

PORT="${VSCODE_PORT:-8080}"
CS452_HOME="/home/cs452"
DEFAULT_FOLDER="${WORKBENCH_HOME:-/home/cs452/projects}"

seed_home() {
	if [ ! -f "${CS452_HOME}/.darcyos-seeded" ]; then
		mkdir -p "${DEFAULT_FOLDER}"
		for f in .bashrc .profile .bash_logout; do
			[ -f "${CS452_HOME}/${f}" ] || cp "/etc/skel/${f}" "${CS452_HOME}/${f}" 2>/dev/null || true
		done
		touch "${CS452_HOME}/.darcyos-seeded"
	fi
	mkdir -p "${DEFAULT_FOLDER}"
}

seed_home
FOLDER="$(cd "${1:-${DEFAULT_FOLDER}}" && pwd)"

seed_vscode_settings() {
	local server_dir="${CS452_HOME}/.vscode-server"
	local settings_dir="${server_dir}/data/Machine"
	mkdir -p "${settings_dir}"
	# Dev workbench: skip "folder is not trusted" for /home/cs452/projects.
	python3 - <<'PY' "${settings_dir}/settings.json"
import json, pathlib, sys
path = pathlib.Path(sys.argv[1])
settings = {}
if path.exists():
	try:
		settings = json.loads(path.read_text())
	except json.JSONDecodeError:
		settings = {}
settings["security.workspace.trust.enabled"] = False
settings["security.workspace.trust.startupPrompt"] = "never"
settings["security.workspace.trust.emptyWindow"] = True
path.write_text(json.dumps(settings, indent=2) + "\n")
PY
}

seed_vscode_settings

print_urls() {
	echo "VS Code — open in your browser:" >&2
	echo "  http://localhost:${PORT}" >&2
	echo "  http://darcyos-dev:${PORT}" >&2
	if command -v hostname >/dev/null 2>&1; then
		for ip in $(hostname -I 2>/dev/null); do
			[ -n "${ip}" ] && echo "  http://${ip}:${PORT}" >&2
		done
	fi
	echo "Default folder: ${FOLDER}" >&2
}

echo "Refreshing apt package lists..." >&2
sudo apt-get update -qq

print_urls

exec /usr/local/bin/code-real serve-web \
	--host 0.0.0.0 \
	--port "${PORT}" \
	--server-data-dir "${CS452_HOME}/.vscode-server" \
	--default-folder "${FOLDER}" \
	--accept-server-license-terms \
	--without-connection-token
