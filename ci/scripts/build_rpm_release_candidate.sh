#!/usr/bin/env bash
# Build and verify Fedora-family RPM candidates from the packaged source archive.
set -euo pipefail

arch="${1:?usage: build_rpm_release_candidate.sh <x64|arm64> [version]}"
case "$arch" in
  x64) expected_rpm_arch="x86_64" ;;
  arm64) expected_rpm_arch="aarch64" ;;
  *) printf 'Unsupported RPM release architecture: %s\n' "$arch" >&2; exit 2 ;;
esac

repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repository_root"
version="${2:-$(awk -F '"' '/^[[:space:]]*version[[:space:]]*=/ {print $2; exit}' pyproject.toml)}"
test -n "$version"

actual_arch="$(rpm --eval '%{_arch}')"
if [[ "$actual_arch" != "$expected_rpm_arch" ]]; then
  printf 'Expected RPM architecture %s, got %s.\n' "$expected_rpm_arch" "$actual_arch" >&2
  exit 2
fi

rm -rf build dist rpm-build release-out/rpm-"$arch"
python3 -m build --sdist --no-isolation
source_archive="dist/onboard-${version}.tar.gz"
test -f "$source_archive"

topdir="$repository_root/rpm-build"
mkdir -p "$topdir"/{BUILD,BUILDROOT,RPMS,SOURCES,SPECS,SRPMS}
install -m 0644 "$source_archive" "$topdir/SOURCES/onboard-${version}.tar.gz"
install -m 0644 packaging/fedora/onboard.spec "$topdir/SPECS/onboard.spec"

rpmbuild -ba --define "_topdir $topdir" "$topdir/SPECS/onboard.spec"

output_directory="release-out/rpm-${arch}"
mkdir -p "$output_directory"
shopt -s nullglob
artifacts=("$topdir"/RPMS/*/*.rpm "$topdir"/SRPMS/*.src.rpm)
if (( ${#artifacts[@]} == 0 )); then
  printf 'No RPM artifacts were produced.\n' >&2
  exit 1
fi

primary_seen=false
for artifact in "${artifacts[@]}"; do
  package_name="$(rpm -qp --qf '%{NAME}' "$artifact")"
  package_version="$(rpm -qp --qf '%{VERSION}' "$artifact")"
  package_arch="$(rpm -qp --qf '%{ARCH}' "$artifact")"
  if [[ "$package_version" != "$version" ]]; then
    printf 'Unexpected RPM version for %s: %s\n' "$package_name" "$package_version" >&2
    exit 1
  fi
  if [[ "$package_name" == "onboard" && "$package_arch" == "$expected_rpm_arch" ]]; then
    rpm -qlp "$artifact" | grep -q '^/usr/bin/onboard$'
    primary_seen=true
  fi
  install -m 0644 "$artifact" "$output_directory/"
done
if [[ "$primary_seen" != true ]]; then
  printf 'The primary onboard RPM was not produced for %s.\n' "$expected_rpm_arch" >&2
  exit 1
fi

python3 ci/scripts/write_sbom.py --version "$version" --output "$output_directory/sbom.cdx.json"
python3 ci/scripts/write_release_manifest.py \
  --input "$output_directory" \
  --output "$output_directory/release-manifest.json" \
  --target-os linux-rpm \
  --target-arch "$arch" \
  --version "$version"
sha256sum "$output_directory"/* > "$output_directory/SHA256SUMS"
printf 'Verified RPM candidate written to %s\n' "$output_directory"
