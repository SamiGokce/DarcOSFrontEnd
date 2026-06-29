#!/usr/bin/env bash
# `code .` opens the current folder in the browser via serve-web; other args pass through.
set -euo pipefail

REAL=/usr/local/bin/code-real

if [ "$#" -eq 1 ] && { [ "$1" = "." ] || [ -d "$1" ]; }; then
	workspace=$([ "$1" = "." ] && pwd || cd "$1" && pwd)
	exec /usr/local/bin/start-vscode.sh "${workspace}"
fi

exec "${REAL}" "$@"
