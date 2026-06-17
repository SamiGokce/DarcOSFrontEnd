#!/usr/bin/env bash
# Install build dependencies on an Arch Linux host for DarcOS development.

set -euo pipefail

PACKAGES=(
    archiso
    shellcheck
    bats
)

echo "Installing DarcOS development dependencies..."
sudo pacman -S --needed --noconfirm "${PACKAGES[@]}"
echo "Done. Run 'make test' to validate the profile, 'make build' to create the ISO."
