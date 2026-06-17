#!/usr/bin/env bash
#
# DarcOS install backend — drives a friendly install (GUI or voice front-ends
# call this). The defining feature: a persistent DARCOS_SOUL partition that is
# PRESERVED across installs, so the agent's identity/memory survives a reinstall.
#
# SAFETY (layered):
#   * plan-first — `plan` only inspects + prints; it never writes.
#   * `disk-prep` / `commit` require a confirmation token matching the target.
#   * refuses to touch the disk currently backing the live root filesystem.
#   * the SOUL partition is only created when absent; never reformatted.
#
# Partition scheme (GPT), all labeled so reinstall can find them:
#   ESP   512M  fat32  LABEL=DARCOS_ESP    — bootloader   (reformatted)
#   ROOT  rest  ext4   LABEL=DARCOS_ROOT   — the OS       (reformatted)
#   SOUL  8G    ext4   LABEL=DARCOS_SOUL   — the agent    (created once, KEPT)
#
# Subcommands:
#   plan <disk>                          inspect + print plan (safe)
#   disk-prep <disk> --confirm <tok>     partition/format/mount + seed soul
#   commit    <disk> --confirm <tok>     disk-prep + pacstrap + configure
#

set -uo pipefail

MNT="/mnt"
ESP_LABEL="DARCOS_ESP"; ROOT_LABEL="DARCOS_ROOT"; SOUL_LABEL="DARCOS_SOUL"
PERSONA="${DARCOS_INSTALL_PERSONA:-samantha}"
USERNAME="${DARCOS_INSTALL_USER:-}"
HOSTNAME_="${DARCOS_INSTALL_HOST:-darcos}"

log()  { echo "[darcos-install] $*"; }
plan() { echo "  • $*"; }
die()  { echo "[darcos-install] ERROR: $*" >&2; exit 1; }

soul_exists() { blkid -L "${SOUL_LABEL}" &>/dev/null; }

# Map disk + index to its partition node (sda1 vs nvme0n1p1 vs loop0p1).
part_dev() {
    local disk="$1" idx="$2"
    [[ "${disk}" =~ [0-9]$ ]] && echo "${disk}p${idx}" || echo "${disk}${idx}"
}

# Ensure /dev partition nodes exist after partitioning. On a normal boot udev
# makes these; in minimal environments (containers without udev) we create them
# from sysfs so mkfs/mount can find them.
ensure_part_nodes() {
    local disk="$1" base d name mm
    base="$(basename "${disk}")"
    for d in /sys/block/"${base}"/"${base}"*; do
        [[ -r "${d}/dev" ]] || continue
        name="$(basename "${d}")"
        [[ -b "/dev/${name}" ]] && continue
        mm="$(cat "${d}/dev")"
        mknod "/dev/${name}" b "${mm%:*}" "${mm#*:}" 2>/dev/null || true
    done
}

require_root() { [[ "${EUID}" -eq 0 ]] || die "must run as root."; }

# Never wipe the disk hosting the running system.
guard_not_live_disk() {
    local disk="$1" rootsrc
    rootsrc="$(findmnt -no SOURCE / 2>/dev/null || true)"
    if [[ -n "${rootsrc}" && "${rootsrc}" == "${disk}"* ]]; then
        die "${disk} backs the live root filesystem — refusing."
    fi
}

check_token() {
    local disk="$1" token="$2" want="erase-$(basename "${disk}")"
    [[ "${token}" == "${want}" ]] || die "confirmation token must be exactly '${want}'."
    [[ -b "${disk}" ]] || die "not a block device: ${disk}"
}

# ── plan ────────────────────────────────────────────────────────────────────
show_plan() {
    local disk="$1"
    log "Install target: ${disk}"
    if soul_exists; then
        plan "SOUL $(blkid -L "${SOUL_LABEL}") → PRESERVE (the agent remembers you)"
        plan "ESP + ROOT → reformat & reinstall"
        log  "Reinstall: the agent's memory/identity is kept."
    else
        plan "Fresh disk → create ESP(512M) + ROOT(rest-8G) + SOUL(8G)"
        plan "SOUL labeled ${SOUL_LABEL}, never wiped on future installs"
        log  "First install: a new soul is created and seeded for the agent."
    fi
    plan "fstab will mount SOUL at /var/lib/darcos; darcos-agentd enabled"
    echo
    log "PLAN ONLY — nothing changed. To proceed:"
    log "  darcos-installer commit ${disk} --confirm erase-$(basename "${disk}")"
}

# ── disk preparation (independently testable) ───────────────────────────────
partition_fresh() {
    local disk="$1"
    log "Partitioning ${disk} (fresh GPT)..."
    sgdisk --zap-all "${disk}" >/dev/null
    sgdisk -n1:0:+512M -t1:ef00 -c1:"${ESP_LABEL}"  "${disk}" >/dev/null
    sgdisk -n2:0:-8G   -t2:8300 -c2:"${ROOT_LABEL}" "${disk}" >/dev/null
    sgdisk -n3:0:0     -t3:8300 -c3:"${SOUL_LABEL}" "${disk}" >/dev/null
    partprobe "${disk}" 2>/dev/null || true
    udevadm settle 2>/dev/null || true
    sleep 1
}

make_filesystems() {
    local disk="$1" fresh="$2"
    local esp root soul
    if [[ "${fresh}" == "yes" ]]; then
        esp="$(part_dev "${disk}" 1)"; root="$(part_dev "${disk}" 2)"; soul="$(part_dev "${disk}" 3)"
    else
        esp="$(blkid -L "${ESP_LABEL}")"; root="$(blkid -L "${ROOT_LABEL}")"; soul="$(blkid -L "${SOUL_LABEL}")"
        [[ -n "${esp}" && -n "${root}" ]] || die "reinstall: can't find existing ${ESP_LABEL}/${ROOT_LABEL}."
    fi

    log "Formatting ESP (${esp}) and ROOT (${root}) — SOUL is left untouched."
    mkfs.fat -F32 -n "${ESP_LABEL}" "${esp}" >/dev/null
    mkfs.ext4 -F -q -L "${ROOT_LABEL}" "${root}"

    if blkid -L "${SOUL_LABEL}" &>/dev/null && [[ "${fresh}" == "no" ]]; then
        log "SOUL already exists at $(blkid -L "${SOUL_LABEL}") — PRESERVED."
    else
        log "Creating new SOUL filesystem on ${soul}."
        mkfs.ext4 -F -q -L "${SOUL_LABEL}" "${soul}"
    fi
}

mount_targets() {
    local root soul esp
    root="$(blkid -L "${ROOT_LABEL}")"; esp="$(blkid -L "${ESP_LABEL}")"; soul="$(blkid -L "${SOUL_LABEL}")"
    mount "${root}" "${MNT}"
    mkdir -p "${MNT}/boot" "${MNT}/var/lib/darcos"
    mount "${esp}" "${MNT}/boot"
    mount "${soul}" "${MNT}/var/lib/darcos"
    log "Mounted ROOT, ESP, and the persistent SOUL under ${MNT}."
}

seed_soul() {
    # Seed identity ON the soul during installation → continuity into use.
    DARCOS_SOUL_DIR="${MNT}/var/lib/darcos" \
        /usr/local/bin/darcos-soul seed --name "${USERNAME:-}" --persona "${PERSONA}" || true
}

disk_prep() {
    local disk="$1"
    require_root
    guard_not_live_disk "${disk}"
    local fresh="yes"; soul_exists && fresh="no"
    if [[ "${fresh}" == "yes" ]]; then partition_fresh "${disk}"; fi
    ensure_part_nodes "${disk}"
    make_filesystems "${disk}" "${fresh}"
    mount_targets
    seed_soul
    log "Disk ready. SOUL is in place and seeded."
}

# ── full install ────────────────────────────────────────────────────────────
install_system() {
    log "Installing base system + DarcOS (pacstrap)..."
    # Package list from the live profile if present, else a sane base.
    local pkgs=(base linux linux-firmware networkmanager sudo)
    [[ -f /usr/share/darcos/packages.x86_64 ]] && \
        mapfile -t pkgs < <(grep -vE '^\s*#|^\s*$' /usr/share/darcos/packages.x86_64)
    pacstrap -c "${MNT}" "${pkgs[@]}"

    log "Copying the DarcOS agent layer onto the installed system..."
    for p in usr/local etc/darcos etc/xdg/autostart usr/share/darcos \
             etc/systemd/system/darcos-agentd.service \
             etc/systemd/system/darcos-boot-splash.service; do
        [[ -e "/${p}" ]] && { mkdir -p "${MNT}/$(dirname "${p}")"; cp -a "/${p}" "${MNT}/${p}"; }
    done
}

configure_system() {
    log "Writing fstab (includes the persistent SOUL mount)..."
    genfstab -U "${MNT}" >> "${MNT}/etc/fstab"

    log "Configuring the installed system (chroot)..."
    arch-chroot "${MNT}" /bin/bash -euo pipefail <<CHROOT
echo "${HOSTNAME_}" > /etc/hostname
ln -sf /usr/share/zoneinfo/UTC /etc/localtime || true
sed -i 's/^#en_US.UTF-8/en_US.UTF-8/' /etc/locale.gen 2>/dev/null || true
locale-gen 2>/dev/null || true
echo "LANG=en_US.UTF-8" > /etc/locale.conf
mkinitcpio -P
systemctl enable NetworkManager.service darcos-agentd.service || true
# Bootloader (systemd-boot on UEFI).
bootctl install || true
cat > /boot/loader/loader.conf <<EOF
default darcos
timeout 3
EOF
mkdir -p /boot/loader/entries
ROOT_UUID=\$(blkid -s UUID -o value -L ${ROOT_LABEL})
cat > /boot/loader/entries/darcos.conf <<EOF
title DarcOS
linux /vmlinuz-linux
initrd /initramfs-linux.img
options root=UUID=\${ROOT_UUID} rw
EOF
CHROOT
    log "System configured. Bootloader installed; darcos-agentd enabled."
}

do_commit() {
    local disk="$1" token="$2"
    require_root
    check_token "${disk}" "${token}"
    guard_not_live_disk "${disk}"
    log "Confirmed. Installing DarcOS to ${disk} (soul preserved)..."
    disk_prep "${disk}"
    install_system
    configure_system
    seed_soul   # re-seed after overlay copy so identity persists on the soul
    log "DarcOS installed. Reboot and the same agent will greet you."
}

# ── dispatch ────────────────────────────────────────────────────────────────
usage() { grep '^#   ' "$0" | sed 's/^#   //'; }

case "${1:-}" in
    plan)      shift; [[ -n "${1:-}" ]] || { usage; exit 1; }; show_plan "$1" ;;
    disk-prep) shift
               disk="${1:-}"; shift || true
               tok=""; [[ "${1:-}" == "--confirm" ]] && tok="${2:-}"
               [[ -n "${disk}" && -n "${tok}" ]] || { usage; exit 1; }
               check_token "${disk}" "${tok}"; disk_prep "${disk}" ;;
    commit)    shift
               disk="${1:-}"; shift || true
               tok=""; [[ "${1:-}" == "--confirm" ]] && tok="${2:-}"
               [[ -n "${disk}" && -n "${tok}" ]] || { usage; exit 1; }
               do_commit "${disk}" "${tok}" ;;
    *) usage; [[ -n "${1:-}" ]] && exit 1 || exit 0 ;;
esac
