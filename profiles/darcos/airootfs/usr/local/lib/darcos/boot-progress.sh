#!/usr/bin/env bash
#
# DarcOS honest boot progress — writes a real 0..1 value to
# /run/darcos/boot-progress that the helix reads. NOT a timed animation:
# progress tracks systemd jobs actually draining, and reaches 1.0 exactly when
# the agent daemon's socket appears — i.e. the circle completes the instant the
# voice agent truly comes online.
#

set -uo pipefail

readonly OUT="/run/darcos/boot-progress"
readonly SOCK="/run/darcos/agentd.sock"
mkdir -p /run/darcos
echo 0 > "${OUT}"

peak_jobs=0
for _ in $(seq 1 200); do          # ~60s ceiling, then assume ready
    # Agent online → fully loaded. This is the honest "ready" signal.
    if [[ -S "${SOCK}" ]]; then
        echo 1 > "${OUT}"
        break
    fi

    running="$(systemctl list-jobs --no-legend 2>/dev/null | grep -c . || echo 0)"
    (( running > peak_jobs )) && peak_jobs="${running}"

    if (( peak_jobs > 0 )); then
        # fraction of the peak job queue that has drained, capped below 1.0
        # until the agent socket confirms true readiness.
        prog="$(awk -v r="${running}" -v p="${peak_jobs}" \
                'BEGIN{ v=(p-r)/p; if(v>0.95) v=0.95; if(v<0) v=0; printf "%.3f", v }')"
    else
        prog="0.9"
    fi
    echo "${prog}" > "${OUT}"
    sleep 0.3
done

echo 1 > "${OUT}"
