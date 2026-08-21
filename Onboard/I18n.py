# -*- coding: utf-8 -*-
#
# Copyright © 2026 Onboard contributors
#
# This file is part of Onboard.
#
# Onboard is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.

"""Internationalization and text-direction helpers.

Gettext selects translated strings, while GTK needs a text direction before
creating menus and windows.  This module keeps locale parsing and direction
selection independent of GTK so it can be tested in headless builds.
"""

from __future__ import division, print_function, unicode_literals

import os


RTL_LANGUAGE_CODES = frozenset((
    "ar",  # Arabic
    "arc", # Aramaic
    "ckb", # Central Kurdish
    "dv",  # Divehi
    "fa",  # Persian
    "he",  # Hebrew
    "ku",  # Kurdish
    "nqo", # N'Ko
    "ps",  # Pashto
    "sd",  # Sindhi
    "ug",  # Uyghur
    "ur",  # Urdu
    "yi",  # Yiddish
))

RTL_SCRIPT_CODES = frozenset((
    "adlm",  # Adlam
    "arab",  # Arabic
    "arabic",  # POSIX modifier form
    "hebr",  # Hebrew
    "hebrew",  # POSIX modifier form
    "mand",  # Mandaic
    "mero",  # Meroitic Cursive
    "nkoo",  # N'Ko
    "rohg",  # Hanifi Rohingya
    "samr",  # Samaritan
    "syrc",  # Syriac
    "thaa",  # Thaana
))

_LOCALE_VARIABLES = ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG")


def normalize_locale_tag(value):
    """Return a lower-case BCP-47-like tag from a POSIX locale value."""
    if not value:
        return ""
    value = str(value).strip()
    if not value or value in ("C", "POSIX"):
        return ""
    # Preserve POSIX modifiers as pseudo-script subtags so ``ku@arabic`` and
    # ``az_Arab`` can select RTL even though their base languages are not RTL.
    value = value.split(".", 1)[0]
    return value.replace("_", "-").replace("@", "-").lower()


def normalize_language_tag(value):
    """Return a lower-case language code from a POSIX/BCP-47 locale value."""
    return normalize_locale_tag(value).split("-", 1)[0]


def locale_tags(environ=None):
    """Yield normalized full locale tags in gettext precedence order."""
    environ = os.environ if environ is None else environ
    for variable in _LOCALE_VARIABLES:
        raw_value = environ.get(variable, "")
        for item in str(raw_value).split(":"):
            tag = normalize_locale_tag(item)
            if tag:
                yield tag


def locale_candidates(environ=None):
    """Yield normalized language candidates in gettext precedence order."""
    for tag in locale_tags(environ):
        yield tag.split("-", 1)[0]


def get_text_direction(environ=None):
    """Return ``rtl`` for RTL languages or RTL script subtags, else ``ltr``."""
    for tag in locale_tags(environ):
        subtags = tag.split("-")
        if subtags[0] in RTL_LANGUAGE_CODES or any(
            subtag in RTL_SCRIPT_CODES for subtag in subtags[1:]
        ):
            return "rtl"
        # The first explicit, non-RTL locale wins, matching gettext fallback
        # semantics and avoiding accidental RTL selection from later fallbacks.
        return "ltr"
    return "ltr"


def is_rtl_locale(environ=None):
    return get_text_direction(environ) == "rtl"


def apply_gtk_text_direction(Gtk, environ=None):
    """Apply the session direction before widgets are created and return it.

    ``Gtk`` is injected to keep importing this module safe in tests and tools
    that do not have PyGObject available.  The operation is idempotent.
    """
    direction = get_text_direction(environ)
    if direction == "rtl":
        Gtk.Widget.set_default_direction(Gtk.TextDirection.RTL)
    else:
        Gtk.Widget.set_default_direction(Gtk.TextDirection.LTR)
    return direction
