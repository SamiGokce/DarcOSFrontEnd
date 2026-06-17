DarcOS
======

A custom Arch Linux distribution built with archiso.

DarcOS ships a minimal live environment with **Hermes Agent** as the default
AI assistant — pre-installed on the ISO and ready after you run `darcos setup`
to choose an LLM provider.

Quick start
-----------

**On Arch Linux:**

```bash
sudo pacman -S archiso
make build
```

**On Fedora / Ubuntu / other distros** (uses Docker or Podman + Arch container):

```bash
make build-container
```

Faster dev build without Hermes download:

```bash
bash scripts/build-container.sh --skip-hermes
```

Output lands in `out/`.

On the live ISO
---------------

```bash
darcos setup    # first run: configure LLM provider
darcos ai       # start Hermes TUI (default)
darcos doctor   # diagnose install issues
```

Hermes is installed system-wide to `/usr/local/lib/hermes-agent` with the
`hermes` command in `/usr/local/bin`. New users receive a seeded config from
`/etc/darcos/hermes-seed`.

Project layout
--------------

```
profiles/darcos/     archiso profile (packages, pacman, overlays)
scripts/             build and Hermes install helpers
config/branding/     logos and theme assets (add your own)
src/__tests__/       profile validation tests
```

Customization
-------------

- **Packages**: edit `profiles/darcos/packages.x86_64`
- **Hermes install**: `profiles/darcos/airootfs/usr/local/lib/darcos/install-hermes.sh`
- **Default AI launcher**: `profiles/darcos/airootfs/usr/local/bin/darcos-ai`
- **Live system files**: add overlays under `profiles/darcos/airootfs/`
- **ISO metadata**: edit `profiles/darcos/profiledef.sh`

Requirements
------------

- Arch Linux host (building archiso ISOs on other distros is unsupported)
- Root privileges for `mkarchiso`
- Network access during ISO build (for Hermes Agent download)
- ~15 GB free disk space (Hermes + build artifacts)

License
-------

MIT — customize freely.
