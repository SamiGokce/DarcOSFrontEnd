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
| nodejs / npm / ttyd | for KatarOS display-screen workflows |

Environment inside container: `XDIR=/opt/toolchain`, `IN_DOCKER=1`, `VSCODE_PORT=8080`, hostname **`darcyos-dev`**. Default shell user: `cs452`.

## Quick start

```bash
docker compose up
```

That builds (if needed), starts **`darcyos-dev`**, and serves VS Code in your browser on port **8080** (`/workspace` is the repo root).

Open **http://localhost:8080** (or the URLs printed in the compose logs).

From another machine on your LAN, use your host IP, e.g. `http://192.168.1.10:8080`.

Change the host port: `VSCODE_PORT=9000 docker compose up`.

For a shell inside the running container:

```bash
docker exec -it darcyos-dev bash
```

To serve a different folder later, run `code .` or `code /path` from inside the container.

## Kernel repo usage

```bash
docker pull codejedi-ai/cs452rotos-platform:latest
cd ../github_codejedi-ai_CS452ROTOS-SMP-DarcyOS
./dev.sh run
```

Or `./dev.sh build-image` to pull (falls back to local `./build.sh` if Hub is unavailable).
