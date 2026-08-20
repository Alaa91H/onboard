#!/usr/bin/env python3
"""Fail a build when a gettext catalog is structurally or semantically incomplete.

The checker intentionally uses GNU gettext command-line utilities already
required by Onboard's build. It is therefore usable in Debian, RPM, Arch, and
Flatpak builds without adding a Python-only translation dependency.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess
import sys


def run(*command: str) -> str:
    completed = subprocess.run(command, check=False, text=True,
                               capture_output=True)
    if completed.returncode:
        sys.stderr.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        raise RuntimeError("command failed: {}".format(" ".join(command)))
    return completed.stdout


def count_entries(po_text: str) -> int:
    return sum(
        1 for line in po_text.splitlines()
        if line.startswith('msgid ') and line != 'msgid ""'
    )


def header_value(catalog: str, key: str) -> str:
    match = re.search(r'^"{}: ([^\\]*)\\n"$'.format(re.escape(key)),
                      catalog, re.MULTILINE)
    return match.group(1) if match else ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog", type=Path)
    parser.add_argument("--require-complete", action="store_true",
                        help="fail when active messages are untranslated")
    parser.add_argument("--language", default="",
                        help="expected catalog language code")
    args = parser.parse_args()

    catalog = args.catalog
    if not catalog.is_file():
        parser.error("catalog does not exist: {}".format(catalog))

    # msgfmt checks syntax, plural forms, and C/Python format placeholders
    # marked by gettext. Keep its diagnostics verbatim for translators.
    run("msgfmt", "--check", "--statistics", str(catalog))
    fuzzy = run("msgattrib", "--no-obsolete", "--only-fuzzy", str(catalog))
    fuzzy_count = count_entries(fuzzy)
    untranslated = run("msgattrib", "--no-obsolete", "--untranslated",
                       str(catalog))
    untranslated_count = count_entries(untranslated)
    source = catalog.read_text(encoding="utf-8")

    if args.language:
        language = header_value(source, "Language")
        if language != args.language:
            raise RuntimeError("expected Language: {}, found: {}"
                               .format(args.language, language or "<missing>"))
    if args.language == "ar":
        plural = header_value(source, "Plural-Forms")
        if "nplurals=6" not in plural:
            raise RuntimeError("Arabic catalog requires six plural forms")

    if fuzzy_count:
        raise RuntimeError("{} fuzzy active gettext entries".format(fuzzy_count))
    if args.require_complete and untranslated_count:
        raise RuntimeError("{} untranslated active gettext entries"
                           .format(untranslated_count))

    print("{}: valid; fuzzy={}, untranslated={}".format(
        catalog, fuzzy_count, untranslated_count))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print("i18n catalog check failed: {}".format(error), file=sys.stderr)
        raise SystemExit(1)
