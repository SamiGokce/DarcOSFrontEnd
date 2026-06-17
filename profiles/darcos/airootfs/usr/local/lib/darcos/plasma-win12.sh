#!/usr/bin/env bash
#
# DarcOS — transform KDE Plasma into the Windows-12 look (the default desktop).
# Centered bottom panel, Start-style launcher, dark + DarcOS accent, Windows
# window-button order, blur, and the agent ("Cortana") as a panel launcher.
#
# Runs inside a user's Plasma session (post-install / first login). Fail-safe:
# if Plasma tools are absent it logs and exits 0. A full Win12 *visual* pack
# (window-decoration + icon theme + look-and-feel) is layered on top of this.
#

set -uo pipefail
log(){ echo "[darcos-win12] $*"; }

have(){ command -v "$1" &>/dev/null; }
KW=kwriteconfig6; have "$KW" || KW=kwriteconfig5
QD=qdbus6;        have "$QD" || QD=qdbus

if ! have "$KW"; then log "Plasma config tools not found; skipping."; exit 0; fi

# ── accent + dark, from the active DarcOS color mode ────────────────────────
mode="warm"; [[ -f /etc/darcos/theme ]] && mode="$(cat /etc/darcos/theme)"
accent="#ff7a4d"
if have jq && [[ -f /usr/share/darcos/themes.json ]]; then
    accent="$(jq -r --arg m "$mode" '.modes[$m].accent // .modes.warm.accent' /usr/share/darcos/themes.json)"
fi
have plasma-apply-colorscheme && plasma-apply-colorscheme BreezeDark &>/dev/null || true
"$KW" --file kdeglobals --group General --key AccentColor "${accent}"
"$KW" --file kdeglobals --group KDE --key SingleClick false        # Windows double-click

# ── Windows-style window controls (min,max,close on the right) ──────────────
"$KW" --file kwinrc --group org.kde.kdecoration2 --key ButtonsOnLeft  ""
"$KW" --file kwinrc --group org.kde.kdecoration2 --key ButtonsOnRight "IAX"
# Blur / translucency for the Mica-like feel.
"$KW" --file kwinrc --group Plugins --key blurEnabled true
"$KW" --file kwinrc --group Plugins --key contrastEnabled true

# ── Windows-12 panel: centered, Start launcher + icon tasks + tray + clock ──
read -r -d '' LAYOUT <<'JS' || true
var p = new Panel;
p.location = "bottom";
p.height = 44;
p.alignment = "center";           // Windows-11/12 centered look
p.addWidget("org.kde.plasma.kickoff");      // Start menu
p.addWidget("org.kde.plasma.icontasks");    // pinned + running, icons only
var tray = p.addWidget("org.kde.plasma.systemtray");
p.addWidget("org.kde.plasma.digitalclock");
JS
# Build the panel only once — re-running would stack duplicate panels.
PANEL_MARKER="${HOME}/.config/darcos-win12-panel.done"
if [[ ! -f "${PANEL_MARKER}" ]] && have "$QD" && "$QD" org.kde.plasmashell &>/dev/null; then
    log "Applying centered Windows-12 panel layout..."
    if "$QD" org.kde.plasmashell /PlasmaShell org.kde.PlasmaShell.evaluateScript "${LAYOUT}" &>/dev/null; then
        touch "${PANEL_MARKER}"
    else
        log "panel layout script failed (apply manually if needed)"
    fi
fi

# ── the agent as 'Cortana': global hotkey + a launcher entry ────────────────
mkdir -p "${HOME}/.local/share/applications"
cat > "${HOME}/.local/share/applications/darcos-agent.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=DarcOS Agent
Comment=Your AI assistant — ask it to do anything
Icon=help-about
Exec=/usr/local/bin/darcos agent
Categories=Utility;
EOF
# Meta+A opens the agent (Windows-key + A, Cortana-style).
"$KW" --file kglobalshortcutsrc --group darcos --key _launch "Meta+A,none,DarcOS Agent" || true

log "Windows-12 transformation applied (mode=${mode}, accent=${accent})."
log "Note: full Win12 visuals (decoration + icon theme) are a look-and-feel pack."
have "$QD" && "$QD" org.kde.KWin /KWin reconfigure &>/dev/null || true
