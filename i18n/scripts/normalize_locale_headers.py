#!/usr/bin/env python3
"""Normalize empty gettext Language headers from canonical catalog filenames."""

from __future__ import annotations

import argparse
from pathlib import Path
import re


EMPTY_LANGUAGE_HEADER = re.compile(r'^("Language: )\\n"$', re.MULTILINE)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog_directory", type=Path)
    parser.add_argument("--write", action="store_true", help="apply the normalization")
    arguments = parser.parse_args()

    catalogs = sorted(arguments.catalog_directory.glob("*.po"))
    if not catalogs:
        parser.error(f"no .po catalogs found in {arguments.catalog_directory}")

    pending: list[Path] = []
    for catalog in catalogs:
        source = catalog.read_text(encoding="utf-8")
        if EMPTY_LANGUAGE_HEADER.search(source):
            pending.append(catalog)
            if arguments.write:
                normalized = EMPTY_LANGUAGE_HEADER.sub(
                    rf'\g<1>{catalog.stem}\\n"', source, count=1
                )
                catalog.write_text(normalized, encoding="utf-8")
    for catalog in pending:
        print(f"{catalog}: Language header -> {catalog.stem}")
    if pending and not arguments.write:
        print("Run again with --write to apply these safe header normalizations.")
        return 1
    print(f"normalized_headers={len(pending)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
