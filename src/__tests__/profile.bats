#!/usr/bin/env bats
# DarcOS profile regression tests — run via: bats src/__tests__/profile.bats

setup() {
    PROFILE="${BATS_TEST_DIRNAME}/../../profiles/darcos"
}

@test "profiledef.sh defines darcos iso name" {
    run grep 'iso_name="darcos"' "${PROFILE}/profiledef.sh"
    [ "$status" -eq 0 ]
}

@test "packages.x86_64 includes base system packages" {
    for pkg in base linux archinstall networkmanager; do
        run grep -qx "${pkg}" "${PROFILE}/packages.x86_64"
        [ "$status" -eq 0 ]
    done
}

@test "darcos-release exports version" {
    run grep 'DARCOS_VERSION=' "${PROFILE}/airootfs/etc/darcos-release"
    [ "$status" -eq 0 ]
}

@test "darcos-install is executable" {
    [ -x "${PROFILE}/airootfs/usr/local/bin/darcos-install" ]
}

@test "automated_script enables NetworkManager" {
    run grep 'NetworkManager' "${PROFILE}/airootfs/root/.automated_script.sh"
    [ "$status" -eq 0 ]
}

@test "darcos-release declares Hermes as default AI" {
    run grep 'DARCOS_DEFAULT_AI="hermes"' "${PROFILE}/airootfs/etc/darcos-release"
    [ "$status" -eq 0 ]
}

@test "automated_script installs Hermes during ISO build" {
    run grep 'install-hermes.sh' "${PROFILE}/airootfs/root/.automated_script.sh"
    [ "$status" -eq 0 ]
}

@test "darcos CLI is executable" {
    [ -x "${PROFILE}/airootfs/usr/local/bin/darcos" ]
}

@test "darcos setup is documented in motd" {
    run grep 'darcos setup' "${PROFILE}/airootfs/etc/motd"
    [ "$status" -eq 0 ]
}

@test "darcos-ai launcher is executable" {
    [ -x "${PROFILE}/airootfs/usr/local/bin/darcos-ai" ]
}

@test "profile.d seeds Hermes for new users" {
    run grep 'hermes-seed' "${PROFILE}/airootfs/etc/profile.d/darcos-hermes.sh"
    [ "$status" -eq 0 ]
}
