#!/usr/bin/env bash
# Build a Linux release candidate from the checked-out source tree.
# Publishing is intentionally outside this script.
set -euo pipefail

TARGET_ARCH=${1:?usage: build_linux_release_candidate.sh <x64|arm64> <version>}
VERSION=${2:?usage: build_linux_release_candidate.sh <x64|arm64> <version>}
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
OUT="$ROOT/release-out/linux-$TARGET_ARCH"

case "$TARGET_ARCH" in
  x64|arm64) ;;
  *) echo "unsupported Linux target architecture: $TARGET_ARCH" >&2; exit 2 ;;
esac

cd "$ROOT"
PACKAGE_VERSION=$(python3 setup.py --version 2>/dev/null | tail -n 1)
if [[ "$VERSION" != "$PACKAGE_VERSION" ]]; then
  echo "candidate version '$VERSION' does not match package version '$PACKAGE_VERSION'" >&2
  exit 2
fi
rm -rf build dist "$OUT"
mkdir -p "$OUT"

./tools/prepare-build-env.sh --with-tests
(cd native/onboard-native && cargo test --locked)
python3 setup.py build
xvfb-run -a python3 -m unittest \
  Onboard.test.test_WaylandCapabilities \
  Onboard.test.test_ClipboardHistory \
  Onboard.test.test_InputSources \
  Onboard.test.test_LayoutLoaderSVG \
  Onboard.test.test_QuickAccess \
  Onboard.test.test_ArabicLocalization \
  Onboard.test.test_NativeInput \
  Onboard.test.test_RTL \
  Onboard.test.test_PlatformBridge
python3 i18n/scripts/check_catalog.py po/ar.po --language ar --require-complete
python3 -m build --no-isolation

wheel=$(find dist -maxdepth 1 -name '*.whl' -print -quit)
sdist=$(find dist -maxdepth 1 -name '*.tar.gz' -print -quit)
test -n "$wheel" && test -n "$sdist"
wheel_listing=$(mktemp)
sdist_listing=$(mktemp)
trap 'rm -f "$wheel_listing" "$sdist_listing"' EXIT
unzip -l "$wheel" > "$wheel_listing"
tar -tzf "$sdist" > "$sdist_listing"
grep -E 'Onboard/onboard_native.*\.so' "$wheel_listing"
grep -q 'share/locale/ar/LC_MESSAGES/onboard.mo' "$wheel_listing"
grep -q 'native/onboard-native/Cargo.lock' "$sdist_listing"

cp "$wheel" "$sdist" "$OUT/"
python3 ci/scripts/write_release_manifest.py \
  --input "$OUT" \
  --output "$OUT/release-manifest.json" \
  --target-os linux --target-arch "$TARGET_ARCH" --version "$VERSION"
sha256sum "$OUT"/* > "$OUT/SHA256SUMS"

echo "Linux release candidate written to $OUT"
