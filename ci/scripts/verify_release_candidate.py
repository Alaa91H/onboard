#!/usr/bin/env python3
"""Validate a Linux release-candidate directory before it is uploaded."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fail(message: str) -> None:
    raise SystemExit("release-candidate verification failed: {}".format(message))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", required=True, type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--target-os", required=True)
    parser.add_argument("--target-arch", required=True)
    args = parser.parse_args()

    directory = args.directory
    manifest_path = directory / "release-manifest.json"
    sbom_path = directory / "sbom.cdx.json"
    checksums_path = directory / "SHA256SUMS"
    for required in (manifest_path, sbom_path, checksums_path):
        if not required.is_file():
            fail("missing {}".format(required.name))

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != 1:
        fail("unsupported manifest schema")
    if manifest.get("project") != "onboard":
        fail("unexpected project")
    if manifest.get("version") != args.version:
        fail("manifest version mismatch")
    target = manifest.get("target", {})
    if target.get("os") != args.target_os:
        fail("manifest target OS mismatch")
    if target.get("architecture") != args.target_arch:
        fail("manifest target architecture mismatch")

    artifacts = manifest.get("artifacts", [])
    by_name = {item.get("name"): item for item in artifacts}
    if len(by_name) != len(artifacts):
        fail("manifest has duplicate artifact names")
    expected_names = {"sbom.cdx.json"}
    expected_names.update(path.name for path in directory.glob("*.whl"))
    expected_names.update(path.name for path in directory.glob("*.tar.gz"))
    if set(by_name) != expected_names:
        fail("manifest artifacts do not match candidate files")

    for name, item in by_name.items():
        artifact = directory / name
        if not artifact.is_file():
            fail("missing manifest artifact {}".format(name))
        if item.get("bytes") != artifact.stat().st_size:
            fail("incorrect size for {}".format(name))
        if item.get("sha256") != sha256(artifact):
            fail("incorrect SHA-256 for {}".format(name))

    sbom = json.loads(sbom_path.read_text(encoding="utf-8"))
    if sbom.get("bomFormat") != "CycloneDX" or sbom.get("specVersion") != "1.5":
        fail("invalid CycloneDX metadata")
    component = sbom.get("metadata", {}).get("component", {})
    if component.get("name") != "onboard" or component.get("version") != args.version:
        fail("SBOM application identity mismatch")

    checksum_names = set()
    for line in checksums_path.read_text(encoding="utf-8").splitlines():
        try:
            _, relative_name = line.split(maxsplit=1)
        except ValueError:
            fail("invalid SHA256SUMS line")
        checksum_names.add(Path(relative_name).name)
    required_checksum_names = expected_names | {"release-manifest.json"}
    if checksum_names != required_checksum_names:
        fail("SHA256SUMS does not cover the complete candidate")

    print("Verified {} release candidate for {} {}.".format(
        args.version, args.target_os, args.target_arch))


if __name__ == "__main__":
    main()
