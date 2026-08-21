#!/usr/bin/env bash
# Build and verify a Flatpak bundle from the checked-out release source.
set -euo pipefail

arch="${1:?usage: build_flatpak_release_candidate.sh <x64|arm64> [version]}"
case "$arch" in
  x64|arm64) ;;
  *) printf 'Unsupported Flatpak release architecture: %s\n' "$arch" >&2; exit 2 ;;
esac

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repository_root"
version="${2:-$(awk -F '"' '/^[[:space:]]*version[[:space:]]*=/ {print $2; exit}' pyproject.toml)}"
test -n "$version"

build_directory="$repository_root/flatpak-build-${arch}"
repository_directory="$repository_root/flatpak-repo-${arch}"
output_directory="$repository_root/release-out/flatpak-${arch}"
rm -rf "$build_directory" "$repository_directory" "$output_directory"
mkdir -p "$output_directory"

flatpak remote-add --if-not-exists --user flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install --user --noninteractive -y flathub \
  org.gnome.Platform//50 org.gnome.Sdk//50 \
  org.freedesktop.Sdk.Extension.rust-stable//25.08

flatpak-builder --force-clean --repo="$repository_directory" \
  "$build_directory" packaging/flatpak/org.onboard.Onboard.yml

# The command intentionally exercises the early JSON diagnostic path, which does
# not require an interactive GTK display inside the Flatpak build sandbox.
diagnostics="$(flatpak build "$build_directory" onboard --diagnose)"
if [[ "$diagnostics" != *'"schema"'* ]]; then
  printf 'Flatpak diagnostic output did not contain the expected schema.\n' >&2
  exit 1
fi

bundle="$output_directory/onboard-${version}-${arch}.flatpak"
flatpak build-bundle "$repository_directory" "$bundle" org.onboard.Onboard
flatpak build-bundle --help >/dev/null

test -s "$bundle"
python3 ci/scripts/write_sbom.py --version "$version" --output "$output_directory/sbom.cdx.json"
python3 ci/scripts/write_release_manifest.py \
  --input "$output_directory" \
  --output "$output_directory/release-manifest.json" \
  --target-os linux-flatpak \
  --target-arch "$arch" \
  --version "$version"
sha256sum "$output_directory"/* > "$output_directory/SHA256SUMS"
printf 'Verified Flatpak candidate written to %s\n' "$output_directory"
