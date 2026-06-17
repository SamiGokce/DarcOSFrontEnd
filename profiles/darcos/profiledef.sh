#!/usr/bin/env bash
# shellcheck disable=SC2034

iso_name="darcos"
iso_label="DARCOS_$(date --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +%Y%m)"
iso_publisher="DarcOS <https://github.com/darcy/DarcOSFrontEnd>"
iso_application="DarcOS Live/Rescue"
iso_version="$(date --date="@${SOURCE_DATE_EPOCH:-$(date +%s)}" +%Y.%m.%d)"
install_dir="darcos"
buildmodes=('iso')
bootmodes=('bios.syslinux.mbr' 'bios.syslinux.eltorito' 'uefi-ia32.systemd-boot.eltorito' 'uefi-x64.systemd-boot.eltorito')
arch="x86_64"
pacman_conf="pacman.conf"
airootfs_image_type="squashfs"
airootfs_image_tool_options=('-comp' 'xz' '-Xbcj' 'x86' '-b' '1M' '-Xdict-size' '1M')
file_permissions=(
  ["/etc/shadow"]="0:0:400"
  ["/root"]="0:0:750"
  ["/root/.automated_script.sh"]="0:0:755"
  ["/root/.gnupg"]="0:0:700"
  ["/usr/local/bin/choose-mirror"]="0:0:755"
  ["/usr/local/bin/Installation_guide"]="0:0:755"
  ["/usr/local/bin/darcos"]="0:0:755"
  ["/usr/local/bin/darcos-install"]="0:0:755"
  ["/usr/local/bin/darcos-ai"]="0:0:755"
  ["/usr/local/bin/darcos-theme"]="0:0:755"
  ["/usr/local/bin/darcos-shell"]="0:0:755"
  ["/usr/local/bin/darcos-agentd"]="0:0:755"
  ["/usr/local/bin/darcos-persona"]="0:0:755"
  ["/usr/local/bin/darcos-voice"]="0:0:755"
  ["/usr/local/bin/darcos-soul"]="0:0:755"
  ["/usr/local/lib/darcos/agentd.py"]="0:0:755"
  ["/usr/local/lib/darcos/installer-backend.sh"]="0:0:755"
  ["/usr/local/bin/livecd-sound"]="0:0:755"
  ["/usr/local/lib/darcos/install-hermes.sh"]="0:0:755"
  ["/usr/local/lib/darcos/hermes-update.sh"]="0:0:755"
  ["/usr/local/lib/darcos/boot-splash.sh"]="0:0:755"
  ["/usr/local/lib/darcos/apply-theme.sh"]="0:0:755"
  ["/usr/local/lib/darcos/welcome.sh"]="0:0:755"
  ["/usr/local/lib/darcos/desktop.sh"]="0:0:755"
  ["/usr/local/lib/darcos/bridge.py"]="0:0:755"
)
