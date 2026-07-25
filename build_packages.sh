#!/bin/bash
# Build script for Onboard packages
# This script builds packages for all supported formats

set -e

SCRIPT_DIR="$(cd -- "$(dirname "$0")" >/dev/null 2>&1; pwd -P)"
BUILD_DIR="$SCRIPT_DIR/build"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print with color
print_status() {
    echo -e "${GREEN}[BUILD]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_warning "Some operations may require root privileges"
    fi
}

# Detect package format support
detect_formats() {
    FORMATS=""
    
    # Check for dpkg (Debian/Ubuntu)
    if command -v dpkg-buildpackage &> /dev/null; then
        FORMATS="$FORMATS debian"
    fi
    
    # Check for rpm (Fedora/openSUSE)
    if command -v rpmbuild &> /dev/null; then
        FORMATS="$FORMATS rpm"
    fi
    
    # Check for flatpak
    if command -v flatpak &> /dev/null; then
        FORMATS="$FORMATS flatpak"
    fi
    
    # Check for snap
    if command -v snapcraft &> /dev/null; then
        FORMATS="$FORMATS snap"
    fi
    
    echo "$FORMATS"
}

# Build Debian packages
build_debian() {
    print_status "Building Debian packages..."
    
    if [ -f "$SCRIPT_DIR/build_debs.sh" ]; then
        /bin/sh "$SCRIPT_DIR/build_debs.sh"
    else
        print_error "build_debs.sh not found"
        return 1
    fi
}

# Build RPM packages
build_rpm() {
    print_status "Building RPM packages..."
    
    SPEC_FILE="$SCRIPT_DIR/packaging/fedora/onboard.spec"
    if [ ! -f "$SPEC_FILE" ]; then
        print_error "RPM spec file not found: $SPEC_FILE"
        return 1
    fi
    
    # Create RPM build directory structure
    mkdir -p ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}
    
    # Copy spec file
    cp "$SPEC_FILE" ~/rpmbuild/SPECS/
    
    # Create source tarball
    python3 setup.py sdist -d ~/rpmbuild/SOURCES/ --formats=gztar
    
    # Build RPM
    rpmbuild -ba ~/rpmbuild/SPECS/onboard.spec
    
    print_status "RPM packages built successfully"
    ls -la ~/rpmbuild/RPMS/*/*.rpm
}

# Build Flatpak
build_flatpak() {
    print_status "Building Flatpak package..."
    
    MANIFEST="$SCRIPT_DIR/packaging/flatpak/org.onboard.Onboard.yml"
    if [ ! -f "$MANIFEST" ]; then
        print_error "Flatpak manifest not found: $MANIFEST"
        return 1
    fi
    
    # Add Flathub remote if not already added
    flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
    
    # Install required runtimes
    flatpak install -y flathub org.freedesktop.Platform//24.08 org.freedesktop.Sdk//24.08 || true
    
    # Build Flatpak
    flatpak-builder --force-clean --repo=repo builddir "$MANIFEST"
    
    # Create bundle
    flatpak build-bundle repo onboard.flatpak org.onboard.Onboard
    
    print_status "Flatpak package built successfully"
    ls -la onboard.flatpak
}

# Build Snap
build_snap() {
    print_status "Building Snap package..."
    
    SNAP_DIR="$SCRIPT_DIR/packaging/snap"
    if [ ! -d "$SNAP_DIR" ]; then
        print_error "Snap packaging directory not found: $SNAP_DIR"
        return 1
    fi
    
    # Build Snap
    cd "$SNAP_DIR"
    snapcraft
    
    print_status "Snap package built successfully"
    ls -la *.snap
}

# Main function
main() {
    print_status "Starting Onboard package build..."
    
    # Check root
    check_root
    
    # Detect available formats
    AVAILABLE_FORMATS=$(detect_formats)
    
    if [ -z "$AVAILABLE_FORMATS" ]; then
        print_error "No supported package formats found"
        print_warning "Please install one of: dpkg, rpmbuild, flatpak, snapcraft"
        exit 1
    fi
    
    print_status "Available formats: $AVAILABLE_FORMATS"
    
    # Create build directory
    mkdir -p "$BUILD_DIR"
    
    # Build packages based on available formats
    for format in $AVAILABLE_FORMATS; do
        case $format in
            debian)
                build_debian
                ;;
            rpm)
                build_rpm
                ;;
            flatpak)
                build_flatpak
                ;;
            snap)
                build_snap
                ;;
        esac
    done
    
    print_status "All available packages built successfully!"
    print_status "Build artifacts are in: $BUILD_DIR"
}

# Run main function
main "$@"
