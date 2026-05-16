#!/usr/bin/env bash
# Deprecated: use ../run.sh dev
exec "$(cd "$(dirname "$0")/.." && pwd)/run.sh" dev "$@"
