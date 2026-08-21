#!/usr/bin/env bash
# Build and verify Debian-family packages from a clean Onboard checkout.
set -euo pipefail

arch="${1:?usage: build_debian_release_candidate.sh <x64|arm64> [version]}"
case "$arch" in
  x64) expected_debian_arch="amd64" ;;
  arm64) expected_debian_arch="arm64" ;;
  *) printf 'Unsupported Debian release architecture: %s\n' "$arch" >&2; exit 2 ;;
esac

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repository_root"

version="${2:-$(awk -F '"' '/^[[:space:]]*version[[:space:]]*=/ {print $2; exit}' pyproject.toml)}"
test -n "$version"
actual_arch="$(dpkg --print-architecture)"
if [[ "$actual_arch" != "$expected_debian_arch" ]]; then
  printf 'Expected Debian architecture %s, got %s.\n' "$expected_debian_arch" "$actual_arch" >&2
  exit 2
fi

debian_version="$(dpkg-parsechangelog -SVersion)"
case "$debian_version" in
  "$version"-*) ;;
  *) printf 'debian/changelog version %s does not match project version %s.\n' "$debian_version" "$version" >&2; exit 2 ;;
esac

rm -rf build debian/.debhelper debian/onboard debian/onboard-common debian/onboard-data \
  debian/gnome-shell-extension-onboard .pybuild
rm -f Onboard/osk*.so Onboard/pypredict/lm*.so
rm -f ../onboard_"$debian_version"_*.deb ../onboard_"$debian_version"_*.buildinfo \
  ../onboard_"$debian_version"_*.changes

dpkg-buildpackage -b -uc -us

output_directory="release-out/debian-${arch}"
rm -rf "$output_directory"
mkdir -p "$output_directory"
shopt -s nullglob
packages=(../onboard_"$debian_version"_*.deb)
if (( ${#packages[@]} == 0 )); then
  printf 'No Debian package was produced for %s.\n' "$debian_version" >&2
  exit 1
fi

primary_seen=false
for package in "${packages[@]}"; do
  package_arch="$(dpkg-deb -f "$package" Architecture)"
  package_name="$(dpkg-deb -f "$package" Package)"
  package_version="$(dpkg-deb -f "$package" Version)"
  if [[ "$package_version" != "$debian_version" ]]; then
    printf 'Unexpected package version for %s: %s\n' "$package_name" "$package_version" >&2
    exit 1
  fi
  if [[ "$package_arch" != "all" && "$package_arch" != "$expected_debian_arch" ]]; then
    printf 'Unexpected package architecture for %s: %s\n' "$package_name" "$package_arch" >&2
    exit 1
  fi
  if [[ "$package_name" == "onboard" && "$package_arch" == "$expected_debian_arch" ]]; then
    listing="$(mktemp)"
    dpkg-deb -c "$package" > "$listing"
    grep -q 'usr/bin/onboard' "$listing"
    rm -f "$listing"
    primary_seen=true
  fi
  install -m 0644 "$package" "$output_directory/"
done
if [[ "$primary_seen" != true ]]; then
  printf 'The primary onboard package was not produced for %s.\n' "$expected_debian_arch" >&2
  exit 1
fi

for metadata in ../onboard_"$debian_version"_*.buildinfo ../onboard_"$debian_version"_*.changes; do
  [[ -f "$metadata" ]] && install -m 0644 "$metadata" "$output_directory/"
done

python3 ci/scripts/write_sbom.py --version "$version" --output "$output_directory/sbom.cdx.json"
python3 ci/scripts/write_release_manifest.py \
  --input "$output_directory" \
  --output "$output_directory/release-manifest.json" \
  --target-os linux-debian \
  --target-arch "$arch" \
  --version "$version"
sha256sum "$output_directory"/* > "$output_directory/SHA256SUMS"
printf 'Verified Debian candidate written to %s\n' "$output_directory"
