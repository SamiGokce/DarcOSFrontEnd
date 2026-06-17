#!/usr/bin/env bash
#
# DarcOS bootstrap — turn an existing Arch system into DarcOS.
#
# Works on ANY Arch base, x86_64 OR aarch64 (Arch Linux ARM) — the DarcOS layer
# is arch-independent. This is the DarcOS ARM edition, mainly for:
#
#   Raspberry Pi (4 / 5, aarch64):
#     1. Flash the official Arch Linux ARM aarch64 image to an SD card.
#     2. Boot the Pi, clone this repo, run:  sudo bash scripts/darcos-bootstrap.sh
#     3. Reboot → DarcOS desktop. (Pi 5 / 4GB+ recommended for Plasma.)
#
#   VMware (aarch64, e.g. Fusion on Apple Silicon):
#     1. Install Arch Linux ARM into the VM.
#     2. Clone + run the bootstrap as above.
#
#   ...and the same script installs DarcOS onto any existing x86_64 Arch box.
#
# Installs: the native desktop, the boot splash, the agent daemon + tools, the
# Windows-12 transform, and a passwordless 'darcos' user with Plasma autologin.
#
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
AF="${ROOT}/profiles/darcos/airootfs"
log() { echo -e "\033[1;38;5;209m●\033[0m $*"; }

[[ "${EUID}" -eq 0 ]] || { echo "Run as root: sudo bash scripts/darcos-bootstrap.sh" >&2; exit 1; }
command -v pacman &>/dev/null || { echo "Not an Arch system (no pacman)." >&2; exit 1; }
[[ -d "${AF}" ]] || { echo "Can't find the DarcOS overlay at ${AF}" >&2; exit 1; }

ARCH="$(uname -m)"
IS_PI=no
if grep -qi "raspberry pi" /proc/device-tree/model 2>/dev/null \
   || grep -qi "raspberry" /proc/cpuinfo 2>/dev/null; then
    IS_PI=yes
fi
log "Bootstrapping DarcOS on ${ARCH}$( [[ "${IS_PI}" == yes ]] && echo ' (Raspberry Pi)' )..."
if [[ "${IS_PI}" == yes ]]; then
    log "Pi detected — Plasma runs best on a Pi 5 or 4GB+ Pi 4. Continuing."
fi

# 1. Packages — arch-independent set (no x86-only microcode/bootloaders here;
#    those belong to the per-arch install, not the DarcOS layer).
PKGS=(
  plasma-desktop sddm dolphin konsole kde-cli-tools xdg-desktop-portal-kde
  plymouth jq python pipewire pipewire-pulse wireplumber networkmanager
  chromium git base-devel
)
log "Installing the native desktop + agent dependencies..."
pacman -Sy --needed --noconfirm "${PKGS[@]}"

# 2. Lay down the DarcOS overlay (agent, scripts, personas, theme, splash, units).
log "Installing the DarcOS layer..."
for p in usr/local usr/share/darcos usr/share/plymouth etc/darcos \
         etc/xdg/autostart etc/systemd/system etc/plymouth; do
    [[ -e "${AF}/${p}" ]] && cp -a "${AF}/${p}/." "/${p}/" 2>/dev/null || \
        { mkdir -p "/${p}"; [[ -e "${AF}/${p}" ]] && cp -a "${AF}/${p}/." "/${p}/"; }
done
chmod +x /usr/local/bin/darcos* /usr/local/lib/darcos/*.sh /usr/local/lib/darcos/*.py 2>/dev/null || true

# 3. Native session: graphical target + SDDM + passwordless Plasma autologin.
log "Configuring the native Plasma (Windows-12) session..."
systemctl set-default graphical.target
systemctl enable sddm.service NetworkManager.service darcos-agentd.service
if ! id darcos &>/dev/null; then
    useradd -m -G wheel,video,audio,network,storage,power -s /bin/bash darcos
    passwd -d darcos
fi
install -d /etc/sddm.conf.d
printf '[Autologin]\nUser=darcos\nSession=plasma\n' > /etc/sddm.conf.d/autologin.conf

# 4. Boot splash (installed system needs the plymouth hook + 'splash' cmdline).
log "Enabling the Plymouth boot splash..."
if ! grep -q plymouth /etc/mkinitcpio.conf 2>/dev/null; then
    sed -i 's/^HOOKS=(base udev/HOOKS=(base udev plymouth/' /etc/mkinitcpio.conf 2>/dev/null || true
fi
mkinitcpio -P 2>/dev/null || true

# 5. Defaults: warm theme + Samantha persona.
echo warm > /etc/darcos/theme 2>/dev/null || true

log "DarcOS bootstrap complete."
log "Reboot → you'll land in the Windows-12 Plasma desktop with the agent."
log "Tip: tell the agent to install anything — 'install firefox' just works."
