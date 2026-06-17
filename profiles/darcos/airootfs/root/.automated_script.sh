#!/usr/bin/env bash
#
# DarcOS automated live environment setup (archiso hook)
#

set -euo pipefail

# Enable NetworkManager on boot
systemctl enable NetworkManager.service

# Native desktop live session: boot into KDE Plasma (Windows-12 themed) via SDDM,
# with a passwordless live user auto-logged in. (SDDM blocks ROOT autologin, so
# we use a dedicated 'darcos' live user.)
systemctl set-default graphical.target
systemctl enable sddm.service
if ! id darcos &>/dev/null; then
    useradd -m -G wheel,video,audio,network,storage,power -s /bin/bash darcos
    passwd -d darcos
fi
install -d /etc/sddm.conf.d
cat > /etc/sddm.conf.d/autologin.conf <<'EOF'
[Autologin]
User=darcos
Session=plasma
EOF

# Refresh mirror list for faster installs (best effort)
if command -v reflector &>/dev/null; then
    reflector --country US --age 12 --protocol https --sort rate --save /etc/pacman.d/mirrorlist || true
fi

# DarcOS branding + Hermes as default AI in shell profile
cat >> /etc/skel/.bashrc <<'EOF'

# DarcOS
[[ -f /etc/darcos-release ]] && source /etc/darcos-release
export DARCOS=1
EOF

# Install Hermes Agent system-wide (requires network during ISO build)
if /usr/local/lib/darcos/install-hermes.sh; then
    echo "DarcOS: Hermes Agent pre-installed."
else
    echo "DarcOS: Hermes Agent install skipped or failed (ISO may lack network during build)."
fi

echo "DarcOS live environment configured."
