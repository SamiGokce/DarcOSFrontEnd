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

| Tool | Version |
|------|---------|
| QEMU `raspi4b` | 9.2.3 |
| `aarch64-none-elf-gcc` | 15.2.rel1 |
| nodejs / npm / ttyd | for KatarOS display-screen workflows |

Environment inside container: `XDIR=/opt/toolchain`, `IN_DOCKER=1`.

## Kernel repo usage

```bash
docker pull codejedi-ai/cs452rotos-platform:latest
cd ../github_codejedi-ai_CS452ROTOS-SMP-DarcyOS
./dev.sh run
```

Or `./dev.sh build-image` to pull (falls back to local `./build.sh` if Hub is unavailable).
