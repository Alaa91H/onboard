#!/usr/bin/env bash
# Build and verify an Arch-family package from the release source archive.
set -euo pipefail

arch="${1:?usage: build_arch_release_candidate.sh <x64|arm64> [version]}"
case "$arch" in
  x64) expected_arch="x86_64" ;;
  arm64) expected_arch="aarch64" ;;
  *) printf 'Unsupported Arch release architecture: %s\n' "$arch" >&2; exit 2 ;;
esac

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repository_root"
version="${2:-$(awk -F '"' '/^[[:space:]]*version[[:space:]]*=/ {print $2; exit}' pyproject.toml)}"
test -n "$version"
if [[ "$(uname -m)" != "$expected_arch" ]]; then
  printf 'Expected Arch architecture %s, got %s.\n' "$expected_arch" "$(uname -m)" >&2
  exit 2
fi

rm -rf build dist arch-build release-out/arch-"$arch"
python3 -m build --sdist --no-isolation
source_archive="dist/onboard-${version}.tar.gz"
test -f "$source_archive"

work_directory="$repository_root/arch-build"
mkdir -p "$work_directory"
install -m 0644 packaging/arch/PKGBUILD "$work_directory/PKGBUILD"
install -m 0644 "$source_archive" "$work_directory/onboard-${version}.tar.gz"

if [[ "${EUID}" -eq 0 ]]; then
  useradd --create-home --shell /bin/bash builder 2>/dev/null || true
  chown -R builder:builder "$work_directory"
  runuser -u builder -- bash -lc "cd '$work_directory' && makepkg --noconfirm --cleanbuild"
else
  (cd "$work_directory" && makepkg --noconfirm --cleanbuild)
fi

output_directory="release-out/arch-${arch}"
mkdir -p "$output_directory"
shopt -s nullglob
packages=("$work_directory"/*.pkg.tar.zst "$work_directory"/*.pkg.tar.xz "$work_directory"/*.pkg.tar.gz)
if (( ${#packages[@]} == 0 )); then
  printf 'No Arch package was produced.\n' >&2
  exit 1
fi

primary_seen=false
for package in "${packages[@]}"; do
  package_name="$(pacman -Qip "$package" | awk -F ': *' '/^Name[[:space:]]*:/ {print $2; exit}')"
  package_arch="$(pacman -Qip "$package" | awk -F ': *' '/^Architecture[[:space:]]*:/ {print $2; exit}')"
  if [[ "$package_name" == "onboard" && "$package_arch" == "$expected_arch" ]]; then
    package_file_list="$(mktemp)"
    bsdtar -tf "$package" > "$package_file_list"
    grep -Fxq 'usr/bin/onboard' "$package_file_list"
    rm -f "$package_file_list"
    primary_seen=true
  fi
  install -m 0644 "$package" "$output_directory/"
done
if [[ "$primary_seen" != true ]]; then
  printf 'The primary onboard package was not produced for %s.\n' "$expected_arch" >&2
  exit 1
fi

python3 ci/scripts/write_sbom.py --version "$version" --output "$output_directory/sbom.cdx.json"
python3 ci/scripts/write_release_manifest.py \
  --input "$output_directory" \
  --output "$output_directory/release-manifest.json" \
  --target-os linux-arch \
  --target-arch "$arch" \
  --version "$version"
sha256sum "$output_directory"/* > "$output_directory/SHA256SUMS"
printf 'Verified Arch candidate written to %s\n' "$output_directory"
