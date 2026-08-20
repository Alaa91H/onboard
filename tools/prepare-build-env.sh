#!/usr/bin/env bash
# Prepare a native build environment for Onboard on major Linux families.
# Run from the source tree: ./tools/prepare-build-env.sh [--with-tests]
set -euo pipefail

with_tests=false
if [[ "${1:-}" == "--with-tests" ]]; then
    with_tests=true
elif [[ $# -gt 0 ]]; then
    echo "Usage: $0 [--with-tests]" >&2
    exit 2
fi

if [[ ${EUID} -eq 0 ]]; then
    SUDO=()
else
    SUDO=(sudo)
fi

install_debian() {
    local packages=(
        build-essential pkg-config gettext intltool
        python3-dev python3-setuptools python3-wheel python3-cairo
        python3-gi python3-gi-cairo python3-dbus
        libgtk-3-dev libxtst-dev libxkbfile-dev libdconf-dev
        libcanberra-dev libhunspell-dev libudev-dev libwayland-dev
        libxkbcommon-dev
    )
    if $with_tests; then
        packages+=(at-spi2-core dconf-cli xautomation numlockx xvfb)
    fi
    "${SUDO[@]}" apt-get update
    "${SUDO[@]}" apt-get install -y "${packages[@]}"
}

install_fedora() {
    local packages=(
        gcc gcc-c++ make pkgconf-pkg-config gettext intltool
        python3-devel python3-setuptools python3-wheel python3-gobject
        python3-cairo python3-dbus
        gtk3-devel libXtst-devel libXkbfile-devel dconf-devel
        libcanberra-devel hunspell-devel systemd-devel wayland-devel
        libxkbcommon-devel
    )
    if $with_tests; then
        packages+=(at-spi2-atk dconf xautomation numlockx xorg-x11-server-Xvfb)
    fi
    "${SUDO[@]}" dnf install -y "${packages[@]}"
}

install_arch() {
    local packages=(
        base-devel pkgconf gettext intltool
        python python-setuptools python-wheel python-gobject python-cairo
        python-dbus gtk3 libxtst libxkbfile dconf libcanberra hunspell
        systemd libxkbcommon wayland
    )
    if $with_tests; then
        packages+=(at-spi2-atk dconf xautomation numlockx xorg-server-xvfb)
    fi
    "${SUDO[@]}" pacman -Syu --needed --noconfirm "${packages[@]}"
}

install_opensuse() {
    local packages=(
        gcc gcc-c++ make pkg-config gettext-tools intltool
        python3-devel python3-setuptools python3-wheel python3-gobject
        python3-cairo python3-dbus
        gtk3-devel libXtst-devel libxkbfile-devel dconf-devel
        libcanberra-devel hunspell-devel systemd-devel wayland-devel
        libxkbcommon-devel
    )
    if $with_tests; then
        packages+=(at-spi2-core dconf xautomation numlockx xorg-x11-server-extra)
    fi
    "${SUDO[@]}" zypper --non-interactive install --no-recommends "${packages[@]}"
}

if command -v apt-get >/dev/null 2>&1; then
    install_debian
elif command -v dnf >/dev/null 2>&1; then
    install_fedora
elif command -v pacman >/dev/null 2>&1; then
    install_arch
elif command -v zypper >/dev/null 2>&1; then
    install_opensuse
else
    cat >&2 <<'EOF'
Unsupported package manager. Install a C/C++ compiler, pkg-config, gettext,
intltool, Python 3 development headers, GTK 3 / GObject introspection bindings,
and the pkg-config development files listed in setup.py.
EOF
    exit 1
fi

printf 'Onboard build prerequisites were installed. Build with: python3 -m build --no-isolation\n'
