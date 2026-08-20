#!/usr/bin/env python3
"""Write a deterministic metadata manifest for build artifacts.

The manifest is intentionally platform-neutral and contains only information
needed to verify a release candidate. Signing and publishing are separate
protected steps, never side effects of a pull-request build.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import subprocess


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_revision(repository: Path) -> str:
    try:
        return subprocess.check_output(
            ["git", "-C", str(repository), "rev-parse", "HEAD"], text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--target-os", required=True)
    parser.add_argument("--target-arch", required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()

    source = args.input
    artifacts = sorted(path for path in source.iterdir() if path.is_file())
    if not artifacts:
        raise SystemExit("no artifacts in {}".format(source))

    payload = {
        "schema": 1,
        "project": "onboard",
        "version": args.version,
        "target": {"os": args.target_os, "architecture": args.target_arch},
        "source_revision": git_revision(Path.cwd()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "build_host": {
            "system": platform.system(),
            "machine": platform.machine(),
            "python": platform.python_version(),
        },
        "artifacts": [
            {"name": item.name, "bytes": item.stat().st_size,
             "sha256": sha256(item)}
            for item in artifacts
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False,
                                      indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")


if __name__ == "__main__":
    main()
