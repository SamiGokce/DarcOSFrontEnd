#!/usr/bin/env bash
#
# DarcOS — apply the active color mode to the GNOME/GTK desktop.
# Reads /etc/darcos/theme + the palette in themes.json and generates:
#   * GTK 3/4 CSS (accent, window, view colors)
#   * a warm radial-gradient wallpaper (SVG) for the mode
#   * gsettings (dark scheme, accent, wallpaper) when a session bus exists
#
# Runs on GNOME login (xdg autostart) and whenever `darcos theme` changes.
# Fails safe: no jq / no session → exits 0 without touching anything.
#

set -uo pipefail

THEMES_JSON="${DARCOS_THEMES_JSON:-/usr/share/darcos/themes.json}"
[[ -f "${THEMES_JSON}" ]] || THEMES_JSON="/etc/darcos/themes.json"

mode="warm"
[[ -f /etc/darcos/theme ]] && mode="$(cat /etc/darcos/theme)"

if ! command -v jq &>/dev/null || [[ ! -f "${THEMES_JSON}" ]]; then
    echo "[darcos-theme] jq or themes.json missing; skipping desktop theming."
    exit 0
fi

get() { jq -r --arg m "${mode}" --arg k "$1" \
        '.modes[$m][$k] // .modes.warm[$k]' "${THEMES_JSON}"; }

BG="$(get bg)"; BG2="$(get bg2)"; ACCENT="$(get accent)"; TEXT="$(get text)"
GLOWA="$(get glowA)"; GLOWB="$(get glowB)"; RING="$(get ring)"

# Map the mode to the closest stock GNOME named accent (GNOME 47+).
case "${mode}" in
    warm) GNOME_ACCENT="orange" ;;
    cool) GNOME_ACCENT="purple" ;;
    *)    GNOME_ACCENT="orange" ;;
esac

# ── GTK 3/4 CSS ────────────────────────────────────────────────────────────
gen_css() {
    cat <<EOF
/* DarcOS ${mode} theme — generated from ${THEMES_JSON##*/}. Do not edit by hand. */
@define-color accent_color ${ACCENT};
@define-color accent_bg_color ${ACCENT};
@define-color accent_fg_color ${BG};
@define-color window_bg_color ${BG};
@define-color window_fg_color ${TEXT};
@define-color view_bg_color ${BG2};
@define-color view_fg_color ${TEXT};
@define-color headerbar_bg_color ${BG2};
@define-color headerbar_fg_color ${TEXT};
@define-color card_bg_color ${BG2};
@define-color popover_bg_color ${BG2};
@define-color sidebar_bg_color ${BG};
EOF
}

for d in gtk-4.0 gtk-3.0; do
    mkdir -p "${HOME}/.config/${d}"
    gen_css > "${HOME}/.config/${d}/gtk.css"
done

# ── wallpaper (warm radial glow) ───────────────────────────────────────────
wall_dir="${HOME}/.local/share/darcos"
wall="${wall_dir}/wallpaper-${mode}.svg"
mkdir -p "${wall_dir}"
cat > "${wall}" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="2560" height="1440" viewBox="0 0 2560 1440">
  <defs>
    <radialGradient id="g" cx="50%" cy="42%" r="75%">
      <stop offset="0%"  stop-color="${BG2}"/>
      <stop offset="55%" stop-color="${BG}"/>
      <stop offset="100%" stop-color="${BG}"/>
    </radialGradient>
    <radialGradient id="glow" cx="50%" cy="42%" r="34%">
      <stop offset="0%"  stop-color="${GLOWA}" stop-opacity="0.22"/>
      <stop offset="60%" stop-color="${GLOWB}" stop-opacity="0.06"/>
      <stop offset="100%" stop-color="${GLOWA}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="2560" height="1440" fill="url(#g)"/>
  <rect width="2560" height="1440" fill="url(#glow)"/>
  <circle cx="1280" cy="605" r="300" fill="none" stroke="${RING}" stroke-opacity="0.12" stroke-width="2"/>
</svg>
EOF

# ── live settings (only with a session bus) ────────────────────────────────
if command -v gsettings &>/dev/null && [[ -n "${DBUS_SESSION_BUS_ADDRESS:-}" ]]; then
    gsettings set org.gnome.desktop.interface color-scheme 'prefer-dark' 2>/dev/null || true
    gsettings set org.gnome.desktop.interface accent-color "${GNOME_ACCENT}" 2>/dev/null || true
    gsettings set org.gnome.desktop.background picture-uri      "file://${wall}" 2>/dev/null || true
    gsettings set org.gnome.desktop.background picture-uri-dark "file://${wall}" 2>/dev/null || true
    gsettings set org.gnome.desktop.background picture-options  'zoom' 2>/dev/null || true
    gsettings set org.gnome.desktop.background primary-color    "${BG}" 2>/dev/null || true
fi

echo "[darcos-theme] applied '${mode}' palette to the desktop."
