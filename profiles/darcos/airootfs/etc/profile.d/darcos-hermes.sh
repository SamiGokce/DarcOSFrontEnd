# DarcOS — Hermes Agent is the default AI assistant.

export DARCOS_DEFAULT_AGENT="hermes"

_darcos_seed_hermes_home() {
    local seed="/etc/darcos/hermes-seed"

    [[ -n "${HOME:-}" ]] || return 0
    [[ -d "${HOME}/.hermes" ]] && return 0
    [[ ! -d "${seed}" ]] && return 0

    mkdir -p "${HOME}/.hermes"
    cp -a "${seed}/." "${HOME}/.hermes/"
    chmod 700 "${HOME}/.hermes"
    [[ -f "${HOME}/.hermes/.env" ]] && chmod 600 "${HOME}/.hermes/.env"
}

_darcos_seed_hermes_home

if [[ -n "${PS1:-}" && -z "${DARCOS_HERMES_HINT_SHOWN:-}" ]]; then
    export DARCOS_HERMES_HINT_SHOWN=1
    if command -v hermes &>/dev/null; then
        echo "DarcOS AI: run 'darcos ai' to start Hermes Agent."
        echo "First time? Run 'darcos setup' to configure your LLM provider."
    fi
fi
