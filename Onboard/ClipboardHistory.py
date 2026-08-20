# -*- coding: UTF-8 -*-
#
# Copyright © 2026 Onboard contributors
#
# This file is part of Onboard.
#
# Onboard is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.

"""Small text-only history for the desktop clipboard.

The history deliberately keeps only text and is process-local. It mirrors the
current system clipboard when an owner changes, and lets the UI select a prior
entry before Onboard sends the standard paste shortcut to the focused app.
"""

from __future__ import division, print_function, unicode_literals

from Onboard.Version import require_gi_versions
require_gi_versions()
from gi.repository import Gdk, Gtk


class ClipboardHistory(object):
    """Track a bounded, de-duplicated list of text clipboard entries."""

    DEFAULT_MAX_ENTRIES = 8

    def __init__(self, clipboard=None, max_entries=DEFAULT_MAX_ENTRIES):
        self._clipboard = clipboard or Gtk.Clipboard.get(
            Gdk.SELECTION_CLIPBOARD)
        self._max_entries = max(1, int(max_entries))
        self._entries = []
        self._owner_change_id = 0

    def start(self):
        if self._clipboard is None:
            return
        if not self._owner_change_id:
            self._owner_change_id = self._clipboard.connect(
                "owner-change", self._on_owner_change)
        self.refresh()

    def cleanup(self):
        if self._clipboard is not None and self._owner_change_id:
            try:
                self._clipboard.disconnect(self._owner_change_id)
            except Exception:
                pass
        self._owner_change_id = 0
        self._clipboard = None

    def refresh(self):
        """Read the current clipboard text and remember it when available."""
        if self._clipboard is None:
            return
        try:
            text = self._clipboard.wait_for_text()
        except Exception:
            return
        self.remember(text)

    def remember(self, text):
        """Add non-empty text to the front, keeping only unique entries."""
        if not isinstance(text, str) or not text:
            return False
        if text in self._entries:
            self._entries.remove(text)
        self._entries.insert(0, text)
        del self._entries[self._max_entries:]
        return True

    def entries(self):
        return self._entries[:]

    def select(self, text):
        """Make a remembered item the current system clipboard content."""
        if not self.remember(text) or self._clipboard is None:
            return False
        try:
            self._clipboard.set_text(text, -1)
            self._clipboard.store()
        except Exception:
            return False
        return True

    def _on_owner_change(self, _clipboard, _event):
        self.refresh()
