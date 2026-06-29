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
    VSCODE_PORT=8080 \
    HOSTNAME=darcyos-dev \
    PATH=/opt/toolchain/bin:/usr/local/bin:/usr/bin:${PATH}

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates xz-utils make bash file git python3 python3-venv \
        build-essential ninja-build pkg-config sudo \
        libglib2.0-dev libpixman-1-dev libfdt-dev zlib1g-dev \
        nodejs npm ttyd wget iproute2 \
        libasound2t64 libatk-bridge2.0-0t64 libatk1.0-0t64 libc6 \
        libcairo2 libcups2t64 libdbus-1-3 libdrm2 libexpat1 libgbm1 \
        libgtk-3-0t64 libnspr4 libnss3 libpango-1.0-0 libx11-6 libxcb1 \
        libxcomposite1 libxdamage1 libxext6 libxfixes3 libxkbcommon0 \
        libxrandr2 xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Passwordless cs452 user (primary login inside the container).
RUN useradd -m -s /bin/bash cs452 \
    && passwd -d cs452 \
    && echo 'cs452 ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/cs452 \
    && chmod 0440 /etc/sudoers.d/cs452

# Hostname is set at runtime via compose (hostname: darcyos-dev) or docker run --hostname.
# VS Code — both x64 and arm64 builds installed; `code` symlinks to the native arch.
RUN set -eux; \
    mkdir -p /tmp/vscode /opt/vscode-linux-x64 /opt/vscode-linux-arm64; \
    wget -q -O /tmp/vscode/code-x64.deb \
        "https://code.visualstudio.com/sha/download?build=stable&os=linux-deb-x64"; \
    wget -q -O /tmp/vscode/code-arm64.deb \
        "https://code.visualstudio.com/sha/download?build=stable&os=linux-deb-arm64"; \
    dpkg-deb -x /tmp/vscode/code-x64.deb /opt/vscode-linux-x64; \
    dpkg-deb -x /tmp/vscode/code-arm64.deb /opt/vscode-linux-arm64; \
    case "$TARGETARCH" in \
        amd64) native=x64 ;; \
        arm64) native=arm64 ;; \
        *) echo "Unsupported TARGETARCH: $TARGETARCH" >&2; exit 1 ;; \
    esac; \
    ln -sf "/opt/vscode-linux-${native}/usr/share/code/bin/code" /usr/local/bin/code-real; \
    ln -sf /opt/vscode-linux-x64/usr/share/code/bin/code /usr/local/bin/code-x64; \
    ln -sf /opt/vscode-linux-arm64/usr/share/code/bin/code /usr/local/bin/code-arm64; \
    rm -rf /tmp/vscode

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

RUN mkdir -p /workspace && chown cs452:cs452 /workspace

COPY scripts/start-vscode.sh /usr/local/bin/start-vscode.sh
COPY scripts/code-wrapper.sh /usr/local/bin/code
RUN sed -i 's/\r$//' /usr/local/bin/start-vscode.sh /usr/local/bin/code \
    && chmod 755 /usr/local/bin/start-vscode.sh /usr/local/bin/code

WORKDIR /workspace
EXPOSE 8080
USER cs452
CMD ["/usr/local/bin/start-vscode.sh", "/workspace"]
