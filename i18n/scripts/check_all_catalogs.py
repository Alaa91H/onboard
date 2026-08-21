#!/usr/bin/env python3
"""Validate every Onboard gettext catalog and report translation health.

Partial community catalogs remain valid: gettext falls back to the source
language for unfinished entries.  The checker treats syntax, headers and
format-field mismatches as errors for every catalog, while languages selected
with ``--require-complete`` must also contain no fuzzy or untranslated active
messages.  This preserves broad language availability without presenting an
incomplete catalog as release-ready.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import gettext
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Iterable


BRACE_FIELD = re.compile(r"\{[^}]*\}")
HEADER_LINE = re.compile(r'^"(?P<key>[^:]+): (?P<value>[^\\]*)\\n"$', re.MULTILINE)


class CatalogError(RuntimeError):
    """Raised when a catalog violates a translation quality contract."""


@dataclass(frozen=True)
class CatalogStatus:
    language: str
    messages: int
    translated: int
    fuzzy: int
    untranslated: int

    @property
    def completion_percent(self) -> float:
        if not self.messages:
            return 100.0
        return (self.translated / self.messages) * 100


def require_tool(name: str) -> None:
    if not shutil.which(name):
        raise CatalogError(f"required gettext tool is unavailable: {name}")


def run(command: Iterable[str], *, cwd: Path) -> str:
    completed = subprocess.run(
        list(command),
        cwd=str(cwd),
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode:
        raise CatalogError(
            "command failed: "
            + " ".join(command)
            + "\n"
            + completed.stdout
            + completed.stderr
        )
    return completed.stdout


def count_entries(catalog: str) -> int:
    return sum(
        1
        for line in catalog.splitlines()
        if line.startswith("msgid ") and line != 'msgid ""'
    )


def header_values(catalog: str) -> dict[str, str]:
    return {
        match.group("key"): match.group("value")
        for match in HEADER_LINE.finditer(catalog)
    }


def ensure_format_fields(catalog: Path, *, cwd: Path) -> None:
    """Check translated brace-format messages after gettext parses the PO file."""
    with tempfile.TemporaryDirectory(prefix="onboard-i18n-") as temporary:
        compiled = Path(temporary) / "onboard.mo"
        run(["msgfmt", "--check", str(catalog), "-o", str(compiled)], cwd=cwd)
        with compiled.open("rb") as source:
            translations = gettext.GNUTranslations(source)
        entries = getattr(translations, "_catalog", {})
        if not isinstance(entries, dict):
            raise CatalogError(f"{catalog.name}: compiled gettext catalog is invalid")
        for message_id, message_string in entries.items():
            if not isinstance(message_id, str) or not isinstance(message_string, str):
                continue
            source_fields = BRACE_FIELD.findall(message_id.split("\x00", 1)[0])
            translated_fields = BRACE_FIELD.findall(message_string.split("\x00", 1)[0])
            if source_fields != translated_fields:
                raise CatalogError(
                    f"{catalog.name}: format fields differ for {message_id!r}: "
                    f"{source_fields!r} != {translated_fields!r}"
                )


def validate_catalog(
    catalog: Path, *, cwd: Path, require_format_match: bool
) -> CatalogStatus:
    source = catalog.read_text(encoding="utf-8")
    headers = header_values(source)
    language = headers.get("Language", "")
    if not language:
        raise CatalogError(f"{catalog.name}: missing Language header")
    catalog_base = catalog.stem.split("@", 1)[0]
    catalog_languages = {catalog.stem, catalog_base}
    regional_base_matches = (
        "_" not in catalog_base and language.split("_", 1)[0] == catalog_base
    )
    if language not in catalog_languages and not regional_base_matches:
        raise CatalogError(
            f"{catalog.name}: Language header {language!r} does not match catalog name"
        )
    if language == "ar" and "nplurals=6" not in headers.get("Plural-Forms", ""):
        raise CatalogError("ar.po: Arabic requires six plural forms")

    run(
        ["msgfmt", "--check", "--statistics", "-o", os.devnull, str(catalog)],
        cwd=cwd,
    )
    if require_format_match:
        ensure_format_fields(catalog, cwd=cwd)
    fuzzy = count_entries(
        run(["msgattrib", "--no-obsolete", "--only-fuzzy", str(catalog)], cwd=cwd)
    )
    untranslated = count_entries(
        run(["msgattrib", "--no-obsolete", "--untranslated", str(catalog)], cwd=cwd)
    )
    messages = count_entries(source)
    translated = max(messages - untranslated, 0)
    return CatalogStatus(
        language=language,
        messages=messages,
        translated=translated,
        fuzzy=fuzzy,
        untranslated=untranslated,
    )


def write_markdown_report(statuses: list[CatalogStatus], destination: Path) -> None:
    lines = [
        "# Onboard Translation Health",
        "",
        "This report is generated by `i18n/scripts/check_all_catalogs.py`. "
        "All catalogs below pass gettext syntax and header validation. "
        "Release-complete catalogs also pass strict format-field validation; "
        "incomplete entries fall back to the source language at runtime.",
        "",
        "| Language | Messages | Translated | Completion | Fuzzy | Untranslated |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for status in statuses:
        lines.append(
            "| {language} | {messages} | {translated} | {completion:.1f}% | "
            "{fuzzy} | {untranslated} |".format(
                language=status.language,
                messages=status.messages,
                translated=status.translated,
                completion=status.completion_percent,
                fuzzy=status.fuzzy,
                untranslated=status.untranslated,
            )
        )
    lines.extend(
        [
            "",
            "> A catalog is release-complete only when it has no fuzzy or "
            "untranslated active entries. Arabic is enforced as complete in CI.",
            "",
        ]
    )
    destination.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("catalog_directory", type=Path)
    parser.add_argument(
        "--require-complete",
        action="append",
        default=[],
        metavar="LANGUAGE",
        help="fail if this language has fuzzy or untranslated active messages",
    )
    parser.add_argument("--report", type=Path, help="write a Markdown health report")
    parser.add_argument("--json", type=Path, dest="json_report", help="write JSON data")
    arguments = parser.parse_args()

    catalog_directory = arguments.catalog_directory.resolve()
    if not catalog_directory.is_dir():
        parser.error(f"catalog directory does not exist: {catalog_directory}")
    for tool in ("msgfmt", "msgattrib"):
        require_tool(tool)
    catalogs = sorted(catalog_directory.glob("*.po"))
    if not catalogs:
        parser.error(f"no .po catalogs found in {catalog_directory}")

    complete_languages = set(arguments.require_complete)
    statuses = [
        validate_catalog(
            catalog,
            cwd=catalog_directory.parent,
            require_format_match=catalog.stem in complete_languages,
        )
        for catalog in catalogs
    ]
    failures = [
        status
        for status in statuses
        if status.language in complete_languages
        and (status.fuzzy or status.untranslated)
    ]
    if failures:
        details = ", ".join(
            f"{status.language}: fuzzy={status.fuzzy}, untranslated={status.untranslated}"
            for status in failures
        )
        raise CatalogError("release-complete catalogs are incomplete: " + details)

    if arguments.report:
        write_markdown_report(statuses, arguments.report)
    if arguments.json_report:
        payload = [
            {
                **asdict(status),
                "completion_percent": round(status.completion_percent, 1),
            }
            for status in statuses
        ]
        arguments.json_report.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    for status in statuses:
        print(
            "{language}: valid; translated={translated}/{messages}; "
            "fuzzy={fuzzy}; untranslated={untranslated}".format(**asdict(status))
        )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CatalogError as error:
        print(f"i18n catalog check failed: {error}", file=sys.stderr)
        raise SystemExit(1)
