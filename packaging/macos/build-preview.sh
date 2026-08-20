#!/usr/bin/env bash
set -euo pipefail

architecture="${1:-$(uname -m)}"
version="${2:-0.1.0}"
repository_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
manifest_path="$repository_root/next/Cargo.toml"
binary_path="$repository_root/next/target/release/onboard-next"
output_root="$repository_root/release-out/macos/$architecture"
app_path="$output_root/Onboard-next.app"
contents_path="$app_path/Contents"
macos_path="$contents_path/MacOS"
resources_path="$contents_path/Resources"

cd "$repository_root"
cargo test --manifest-path "$manifest_path" --workspace --locked
cargo build --manifest-path "$manifest_path" --bin onboard-next --release --locked

if [[ ! -x "$binary_path" ]]; then
  printf 'Expected macOS binary was not created: %s\n' "$binary_path" >&2
  exit 1
fi

rm -rf "$app_path"
mkdir -p "$macos_path" "$resources_path"
install -m 0755 "$binary_path" "$macos_path/onboard-next"

cat > "$contents_path/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>CFBundleDevelopmentRegion</key>
  <string>en</string>
  <key>CFBundleExecutable</key>
  <string>onboard-next</string>
  <key>CFBundleIdentifier</key>
  <string>org.onboard.OnboardNext</string>
  <key>CFBundleInfoDictionaryVersion</key>
  <string>6.0</string>
  <key>CFBundleName</key>
  <string>Onboard-next Preview</string>
  <key>CFBundlePackageType</key>
  <string>APPL</string>
  <key>CFBundleShortVersionString</key>
  <string>$version</string>
  <key>CFBundleVersion</key>
  <string>$version</string>
  <key>LSMinimumSystemVersion</key>
  <string>12.0</string>
</dict>
</plist>
PLIST

plutil -lint "$contents_path/Info.plist"
diagnostics="$($macos_path/onboard-next diagnose ar_SA)"
if [[ "$diagnostics" != *'"direction":"rtl"'* ]]; then
  printf 'Arabic RTL diagnostic failed for the macOS preview binary.\n' >&2
  exit 1
fi

commit="$(git rev-parse HEAD)"
cat > "$resources_path/provenance.json" <<JSON
{
  "product": "onboard-next",
  "channel": "preview",
  "platform": "macos",
  "architecture": "$architecture",
  "version": "$version",
  "commit": "$commit",
  "signed": false,
  "notarized": false,
  "input_source": "read-only-tis-pending",
  "notes": "Preview bridge build. Do not treat as a signed or notarized stable application."
}
JSON

(
  cd "$output_root"
  find "Onboard-next.app" -type f -print0 | sort -z | xargs -0 shasum -a 256 > SHA256SUMS
)
printf 'macOS preview app created: %s\n' "$app_path"
