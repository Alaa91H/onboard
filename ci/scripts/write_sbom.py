#!/usr/bin/env python3
"""Generate a compact CycloneDX SBOM from tracked Python and Rust metadata."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import tomllib


def component(name: str, version: str, ecosystem: str, component_type: str = "library"):
    qualifier = "pypi" if ecosystem == "pypi" else "cargo"
    return {
        "type": component_type,
        "name": name,
        "version": version,
        "purl": "pkg:{}/{}@{}".format(qualifier, name, version),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--cargo-lock", default="native/onboard-native/Cargo.lock",
                        type=Path)
    args = parser.parse_args()

    lock = tomllib.loads(args.cargo_lock.read_text(encoding="utf-8"))
    rust_components = []
    for package in lock.get("package", []):
        name = package.get("name")
        version = package.get("version")
        if name and version:
            rust_components.append(component(name, version, "cargo"))

    # Deduplicate package records while retaining deterministic order.
    indexed = {(item["name"], item["version"], item["purl"]): item
               for item in rust_components}
    components = [component("onboard", args.version, "pypi", "application")]
    components.extend(indexed[key] for key in sorted(indexed))

    document = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.5",
        "serialNumber": "urn:uuid:onboard-{}".format(args.version),
        "version": 1,
        "metadata": {
            "component": component("onboard", args.version, "pypi",
                                   "application"),
        },
        "components": components,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(document, ensure_ascii=False,
                                      indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")


if __name__ == "__main__":
    main()
