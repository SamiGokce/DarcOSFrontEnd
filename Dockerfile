# syntax=docker/dockerfile:1
#
# CS452ROTOS-PLATFORM — shared dev image for every kernel repo.
#
# Multi-arch: build for linux/amd64 (x64) and/or linux/arm64 (ARM) hosts.
#   ./build.sh              # native host only
#   ./build.sh --all        # both architectures (tags :amd64 and :arm64)
#
# Locked versions (tarballs in deps/, shared with NyxOS (CS452ROTOS-NYXOS)):
#   QEMU          9.2.3  (raspi4b)
#   ARM toolchain 15.2.rel1 aarch64-none-elf (host x86_64 or aarch64 tarball)

FROM ubuntu:24.04

ARG QEMU_VER=9.2.3
ARG TC_VER=15.2.rel1
ARG TARGETARCH

ENV DEBIAN_FRONTEND=noninteractive \
    XDIR=/opt/toolchain \
    IN_DOCKER=1 \
    PATH=/opt/toolchain/bin:/usr/local/bin:/usr/bin:${PATH}

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates xz-utils make bash file git python3 python3-venv \
        build-essential ninja-build pkg-config \
        libglib2.0-dev libpixman-1-dev libfdt-dev zlib1g-dev \
        nodejs npm ttyd \
    && rm -rf /var/lib/apt/lists/*

# QEMU 9.2.3 from committed tarball (no apt/git rebuild on every image bump).
RUN --mount=type=bind,source=deps,target=/tmp/deps \
    set -eux; \
    tar -xf "/tmp/deps/qemu-${QEMU_VER}.tar.xz" -C /tmp; \
    cd "/tmp/qemu-${QEMU_VER}"; \
    ./configure --prefix=/usr/local --target-list=aarch64-softmmu \
        --disable-werror --disable-docs --disable-gtk --disable-sdl \
        --disable-vnc --disable-curses --disable-xen --disable-kvm; \
    make -j"$(nproc)"; \
    make install; \
    rm -rf "/tmp/qemu-${QEMU_VER}"; \
    qemu-system-aarch64 -M help | grep -q raspi4b

# ARM GNU bare-metal toolchain — host tarball selected from TARGETARCH (x64 vs ARM).
RUN --mount=type=bind,source=deps,target=/tmp/deps \
    set -eux; \
    case "$TARGETARCH" in \
        amd64) HOST=x86_64 ;; \
        arm64) HOST=aarch64 ;; \
        *) echo "Unsupported TARGETARCH: $TARGETARCH (use linux/amd64 or linux/arm64)" >&2; exit 1 ;; \
    esac; \
    mkdir -p /opt/toolchain; \
    tar -xf "/tmp/deps/arm-gnu-toolchain-${TC_VER}-${HOST}-aarch64-none-elf.tar.xz" \
        -C /opt/toolchain --strip-components=1; \
    /opt/toolchain/bin/aarch64-none-elf-gcc --version

WORKDIR /workspace
CMD ["bash"]
