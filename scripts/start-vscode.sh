#!/usr/bin/env bash
# Serve VS Code in the browser for a workspace folder.
set -euo pipefail

PORT="${VSCODE_PORT:-8080}"
WORKSPACE="$(cd "${1:-.}" && pwd)"

print_urls() {
	echo "VS Code — open in your browser:" >&2
	echo "  http://localhost:${PORT}" >&2
	echo "  http://darcyos-dev:${PORT}" >&2
	if command -v hostname >/dev/null 2>&1; then
		for ip in $(hostname -I 2>/dev/null); do
			[ -n "${ip}" ] && echo "  http://${ip}:${PORT}" >&2
		done
	fi
	echo "Workspace: ${WORKSPACE}" >&2
}

print_urls

exec /usr/local/bin/code-real serve-web \
	--host 0.0.0.0 \
	--port "${PORT}" \
	--accept-server-license-terms \
	--without-connection-token
