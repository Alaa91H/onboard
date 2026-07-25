# Onboard Packaging

This directory contains packaging files for building Onboard packages in various formats.

## Available Formats

### 1. Debian/Ubuntu (.deb)
Location: `debian/`

To build Debian packages:
```bash
./build_debs.sh
```

The packages will be created in `build/debs/`.

### 2. Fedora/RHEL (.rpm)
Location: `packaging/fedora/onboard.spec`

To build RPM packages:
```bash
# Install dependencies
sudo dnf install -y rpm-build

# Build RPM
rpmbuild -ba packaging/fedora/onboard.spec
```

### 3. Flatpak
Location: `packaging/flatpak/org.onboard.Onboard.yml`

To build Flatpak package:
```bash
# Install dependencies
sudo apt install flatpak flatpak-builder

# Add Flathub remote
flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo

# Build Flatpak
flatpak-builder --force-clean --repo=repo builddir packaging/flatpak/org.onboard.Onboard.yml

# Create bundle
flatpak build-bundle repo onboard.flatpak org.onboard.Onboard
```

### 4. Snap
Location: `packaging/snap/snapcraft.yaml`

To build Snap package:
```bash
# Install Snapcraft
sudo snap install snapcraft --classic

# Build Snap
cd packaging/snap
snapcraft
```

## Automated Builds

This project uses GitHub Actions to automatically build all package formats. The workflow file is located at:
`.github/workflows/build-packages.yml`

### Triggering Builds

- **Push to main/master**: Builds all packages
- **Pull requests**: Builds all packages
- **Tagged releases (v*)**: Builds all packages and creates a GitHub Release

### Build Artifacts

All build artifacts are uploaded as GitHub Actions artifacts and can be downloaded from the workflow runs.

## Manual Build

To build all available packages manually:
```bash
./build_packages.sh
```

This script will detect which package formats are available on your system and build them automatically.

## Package Descriptions

### onboard
The main Onboard package containing the on-screen keyboard application.

### onboard-common
Architecture-independent files for Onboard.

### onboard-data
Language model files for the word suggestion feature.

### gnome-shell-extension-onboard
GNOME Shell extension for Onboard integration.

## Dependencies

### Build Dependencies
- Python 3.6+
- gcc/g++
- pkg-config
- GTK 3 development files
- libxtst development files
- libxkbfile development files
- libdconf development files
- libcanberra development files
- libhunspell development files
- libudev development files
- python3-distutils-extra
- python3-packaging

### Runtime Dependencies
- Python 3.6+
- python3-gobject
- python3-cairo
- python3-dbus
- iso-codes
- librsvg2
- GNOME Shell (optional, for extension)

## Contributing

When adding new packaging formats or modifying existing ones:

1. Update the appropriate packaging files
2. Test the build process
3. Update this README if necessary
4. Submit a pull request

## License

This packaging is licensed under the same terms as Onboard itself (GPLv3+).
