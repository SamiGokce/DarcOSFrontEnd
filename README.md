# CS452ROTOS-PLATFORM

**Component:** shared development platform (not a kernel OS)  
**Git provider:** codejedi-ai  
**Origin repository:** [github.com/codejedi-ai/CS452ROTOS-PLATFORM](https://github.com/codejedi-ai/CS452ROTOS-PLATFORM)  
**Docker Hub:** `codejedi-ai/cs452rotos-platform:latest`

This is the **only** repo that stores large build inputs (QEMU + toolchain tarballs via **Git LFS**). Kernel repos pull the pre-built image from Docker Hub and do not carry `deps/` or platform Dockerfiles.

## Large files (Git LFS)

```
deps/qemu-9.2.3.tar.xz
deps/arm-gnu-toolchain-15.2.rel1-x86_64-aarch64-none-elf.tar.xz
deps/arm-gnu-toolchain-15.2.rel1-aarch64-aarch64-none-elf.tar.xz
```

```bash
git lfs install
git lfs pull
```

## Multi-architecture (x64 + ARM hosts)

```bash
./build.sh              # native host → local tag darcyos-dev
./build.sh --all        # :amd64 and :arm64
```

## Publish to Docker Hub

```bash
docker login
DOCKERHUB_REPO=codejedi-ai/cs452rotos-platform ./push.sh
```

Pushes `linux/amd64` + `linux/arm64` manifest. Kernel repos default to pulling this image.

## Image contents

Ubuntu 24.04 dev container with passwordless user **`cs452`** (`sudo` without password).

| Tool | Version |
|------|---------|
| QEMU `raspi4b` | 9.2.3 |
| `aarch64-none-elf-gcc` | 15.2.rel1 |
| VS Code (`code`, `code-x64`, `code-arm64`) | stable — both x64 and arm64 builds installed; `code` runs the native arch |
| nodejs / npm | optional tooling in some repos |

Environment inside container: `XDIR=/opt/toolchain`, `IN_DOCKER=1`, `VSCODE_PORT=8080`, hostname **`darcyos-dev`**. Default shell user: `cs452`.

## Quick start

```bash
docker compose up
```

That builds (if needed), starts **`darcyos-dev`**, runs `sudo apt update`, and serves VS Code on port **8080** with **`/home/cs452/projects`** opened by default.

Kernel and other repos live under `/home/cs452/projects`. That folder is persisted in the `cs452-projects` Docker volume.

From another machine on your LAN, use your host IP, e.g. `http://192.168.1.10:8080`.

Change the host port: `VSCODE_PORT=9000 docker compose up`.

For a shell inside the running container:

```bash
docker exec -it darcyos-dev bash
```

To serve a different folder, run `code .` or `code /path` from inside the container.

## Kernel repo usage

Each kernel repo ships an identical terminal-only `./dev.sh` (synced from `scripts/os-dev.sh` in this repo). It bind-mounts the kernel tree at **`/workspace`** inside `codejedi-ai/cs452rotos-platform:latest` and runs the same in-container commands everywhere (`make`, `run`, `test`, `test-k*`, `shell`).

```bash
docker pull codejedi-ai/cs452rotos-platform:latest
cd ../github_codejedi-ai_CS452ROTOS-SMP-DarcyOS
./dev.sh run          # interactive QEMU on your terminal
./dev.sh make all     # build only
./dev.sh test-k4      # milestone tests
```

Or `./dev.sh build-image` to pull (falls back to local `./build.sh` if Hub is unavailable).

Re-sync kernel repos after changing the shared workflow:

```bash
./scripts/sync-os-dev-workflow.sh
```

### Remote / browser dev (PLATFORM only)

This repo may optionally expose **ttyd** or VS Code in the browser (`docker compose up` → port 8080). Kernel repos **never** start ttyd — they only attach QEMU serial to the host terminal. For remote work, run PLATFORM, clone any kernel repo under `/home/cs452/projects`, and use the same `make` / `qemu/run.sh` commands inside that container.
