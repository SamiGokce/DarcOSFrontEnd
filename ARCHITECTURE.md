DarcOS Architecture
===================

DarcOS is **not** a kernel or an OS written from scratch. It is a custom Arch
Linux distribution (built with `archiso`) with an AI agent embedded as a
first-class part of the system, plus an "OS1 from *Her*" experience layer.

The ~4 GB is upstream Linux + packages we merely *select*. The part that is
actually ours is a thin layer: a package list, branding, a boot visual, and the
AI integration.

Two customization axes
----------------------

DarcOS is configured along two independent axes. The AI is embedded in **every**
combination — the desktop is only a skin on top of it.

### 1. Color mode  (`darcos theme`)

Single source of truth: `config/branding/themes.json`. Read by the boot helix,
the TUI, and (eventually) the GTK/KDE theme.

- **warm** — OS1 / *Her*: coral → peach → white glow on warm near-black (default)
- **cool** — DarcOS purple / cyan, warm-biased

State file: `/etc/darcos/theme`.

### 2. Shell mode  (`darcos shell`)

How the human reaches the embedded AI.

- **voice** — no desktop; the Hermes TUI *is* the interface (default, tiny ISO)
- **gnome** — GNOME desktop, AI embedded as a panel/overlay
- **kde**   — KDE Plasma desktop, AI embedded as a panel/overlay

State file: `/etc/darcos/shell`. On the live ISO this records a preference; on an
installed system it also installs the desktop packages and enables the display
manager. Desktop packages are intentionally **not** baked into the base ISO
(keeps it small); they are installed at `darcos install` time per the chosen mode.

The embedded AI
---------------

- **Hermes Agent** is the default, installed system-wide during the ISO build
  (`scripts/install-hermes.sh`). Claude Code and Codex are planned as additional
  installable agents using the same pattern.
- Auto-update: `darcos-hermes-update.timer` (daily, persistent) re-runs the
  Hermes installer to pull the latest release; `darcos update` does it on demand.
- First-run config: `darcos setup` chooses the LLM provider / API key.

The OS1 experience layer
------------------------

- **Boot helix** — `src/boot-helix/index.html`: a 3D double-helix of light that
  winds up and resolves into a glowing circle as load reaches 100%. Three.js,
  self-contained glow (no external image), theme-aware (`?theme=warm|cool`,
  press **T** to toggle live). Driven by real boot progress via
  `window.setBootProgress(0..1)`; falls back to a demo sweep.
- **Boot sound** — `python_loading/os1_bootup.py`: the *Her*-style frequency
  sweep synth.
- **Wired into boot**: `darcos-boot-splash.service` runs `boot-splash.sh` on
  tty1 — plays the pre-rendered chime (`/usr/share/darcos/sounds/os1-boot.wav`)
  and shows the helix via `cage` + `chromium` kiosk, themed from
  `/etc/darcos/theme`. Fails safe (exits 0) if there's no GPU/browser, so it can
  never block boot. Three.js is vendored locally (offline).
- The sound is rendered at build time by `scripts/render-boot-sound.py` (reuses
  the synth math) — no Python/Tk at boot.

GNOME / KDE theming
-------------------

`apply-theme.sh` reads `/etc/darcos/theme` + `themes.json` and generates GTK 3/4
CSS (accent/window/view colors), a warm radial-gradient SVG wallpaper, and
gsettings (dark scheme, named accent: warm→orange, cool→purple). It runs on
login via `/etc/xdg/autostart/darcos-theme.desktop` and re-applies live when
`darcos theme` changes inside a session.

How a boot works (target)
-------------------------

1. `make build` / `make build-container` → `mkarchiso` → `out/darcos.iso`
2. Flash / boot the ISO (VM or USB)
3. Boot loader (`efiboot/`, `grub/`, `syslinux/`) starts Linux
4. Helix visual + *Her* boot sound play during load
5. Lands in the selected shell mode (voice TUI, or GNOME/KDE with AI embedded)
6. The AI agent is the centerpiece in every mode

Testing the ISO
---------------

```bash
make build-container        # build on Fedora/Ubuntu via Docker (you have docker)
sudo pacman -S qemu-desktop # (Arch) or `sudo dnf install qemu-system-x86` on Fedora
qemu-system-x86_64 -enable-kvm -m 4G -cdrom out/darcos-*.iso -boot d
```

To preview just the boot helix without building anything, open
`src/boot-helix/index.html` in a browser (`xdg-open src/boot-helix/index.html`).

North star: the OS *is* the harness (AI full control)
-----------------------------------------------------

DarcOS is not "an OS with an AI app." The AI is the system. A harness =
**tools + context + permissions + loop**, lifted from app-level to OS-level:

- **`darcos-agentd`** — an always-on agent daemon (systemd service). The single
  persistent brain. Every interface (voice, TUI, GUI overlay, global hotkey,
  notifications) is a thin client over its control socket. The OS boots into it.
- **Tools = the whole system** — shell, filesystem, `pacman`, systemd services,
  devices, and the desktop itself via computer-use (`grim` screenshot +
  `ydotool` input). The agent can do anything a root user can.
- **Context = live system state** — running processes, focused window, recent
  files, journal errors, removable media, calendar. Fed continuously so the
  agent is situationally aware and can act proactively.
- **Engine is pluggable** — the daemon delegates reasoning to a configured
  backend (Hermes, or Claude via API for hosted computer-use). DarcOS owns the
  loop, tools, context, and policy; the engine is swappable.

Personalities + emotion engine
------------------------------

The agent has a *self*, not just a function. Personas live in
`/usr/share/darcos/personas/*.json` (`samantha` = warm/present/Her-like, the
default; `darc` = calm operator). A persona defines name, pronouns, a
`system_prompt` (the voice sent to LLM engines), style weights (warmth, brevity,
playfulness), TTS voice, a color mode, and emotion config. Switch with
`darcos persona <id>`.

The **emotion engine** is seeded by the `Affect` core in `agentd.py`: a
(valence, arousal, rapport) mood that drifts toward the persona's baseline and
nudges on outcomes (success lifts, failure dips). Today it tints narration
(`☼` glad / `·` even / `◌` concerned); the roadmap is to condition tone, voice
prosody, and proactive care — so the OS can empathize and connect, like Her.

Install experience (friendly, not Arch-technical)
-------------------------------------------------

Linux installs are notoriously technical; DarcOS makes it a conversation.
`darcos install` offers three front-ends over one backend:

- **Graphical** — a themed, breathing-orb installer
  (`/usr/share/darcos/installer/index.html`) shown in the cage+chromium kiosk,
  theme-aware, with a "Talk to me" button.
- **Voice** — `darcos-voice`: 🎤 capture → STT → `darcos-agentd` → TTS 🔊.
  Samantha installs the OS *for* you. STT/TTS pluggable (whisper/piper offline,
  or **ElevenLabs** cloud for Scribe STT + premium voice — key via `darcos setup`).
- **Classic** — archinstall fallback when there's no GPU/audio.

All three drive `installer-backend.sh`, which is **plan-first**: it prints the
partition plan and only touches a disk with `commit <disk> --confirm erase-<dev>`
— so neither a GUI bug nor a misheard command can wipe a drive.

The persistent soul partition (the agent survives reinstalls)
-------------------------------------------------------------

A dedicated partition `LABEL=DARCOS_SOUL`, mounted at `/var/lib/darcos`, holds
everything that makes the agent *itself*: identity, long-term memory, learned
adaptation to the user, customized personas, secrets, and audit history. The
installer **never wipes it** — only the ROOT partition is reinstalled. So you
can reinstall DarcOS and the agent remembers you ("welcome back").

- `darcos-soul {status|mount|init|seed|format}` manages it; `darcos-agentd`
  mounts it via `ExecStartPre` and prefers it for audit + persona overlays.
- `format` refuses if a soul already exists — souls are never destroyed.
- Without a soul partition the agent still works (state is OS-local, non-persistent).

**Continuity install → use:** the soul/`identity.json` is created and seeded
*during* installation (`darcos-soul seed --name --persona`), stamping
`born_during: install` and a "we set this machine up together" note. Post-install
the same daemon reads it and greets you by name — the agent that installed the
OS *is* the one you keep. (`MOUNT` honors `DARCOS_SOUL_DIR`, matching agentd.)

Honest loading
--------------

The boot helix is NOT a timed animation. `boot-progress.sh` writes a real 0..1
to `/run/darcos/boot-progress` (fraction of systemd jobs drained), and the helix
polls it (XHR, `--allow-file-access-from-files`). The circle completes the
instant the agent socket appears — i.e. the visual "the voice agent comes
online" is the genuine moment it does. Demo sweep is a preview-only fallback.

The safety spine (non-negotiable for "full control")
----------------------------------------------------

Full control means the agent CAN brick the machine, so three guardrails are
load-bearing, not optional:

1. **Policy + consent gate** (`darcos-policy`) — every tool call is classified
   (read / mutate / dangerous) and run through a policy: auto-allow safe reads,
   confirm or auto-act on mutations per the user's chosen autonomy level, always
   refuse-without-explicit-consent for destructive ops (wipe, user/cred changes).
3. **Append-only audit log** — every action the agent takes is recorded
   (`/var/log/darcos/agent-audit.log`) so it's reviewable and reversible.
2. **Never in the boot-critical path** — the daemon is `Wants=`, never
   `Requires=`, of boot. If the agent or its network is down, the OS still boots
   and is fully usable by hand. (Same fail-safe principle as the boot splash.)

Open work
---------

- Claude + Codex installers alongside Hermes (same pattern as install-hermes.sh).
- KDE variant of the theme (the GTK path covers GNOME; KDE needs a kdeglobals
  generator from the same palette).
- Build + boot-test the ISO in QEMU to validate the splash on real hardware/VM.
- Hand boot progress to the helix from real units (`window.setBootProgress`)
  instead of the demo sweep.
