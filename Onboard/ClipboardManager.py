# -*- coding: utf-8 -*-

"""
Clipboard Manager for Onboard
Provides clipboard history, copy/cut/paste support for the floating keyboard.
Inspired by the Windows 11 Touch Keyboard clipboard panel.

Copyright © 2026 Alaa91H

This file is part of Onboard.

Onboard is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

Onboard is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

from __future__ import division, print_function, unicode_literals

import time
import json
import os

from Onboard.Version import require_gi_versions
require_gi_versions()
from gi.repository import GLib, Gdk, Gtk, Pango

from Onboard.utils import Rect

### Logging ###
import logging
_logger = logging.getLogger("ClipboardManager")
###############

### Config Singleton ###
from Onboard.Config import Config
config = Config()
########################


# Default maximum number of clipboard history entries (non-pinned)
DEFAULT_MAX_HISTORY = 100

# Absolute minimum and maximum limits
MIN_HISTORY_LIMIT = 10
MAX_HISTORY_LIMIT = 1000

# File to persist clipboard history
CLIPBOARD_HISTORY_FILE = "clipboard_history.json"

# Settings key for max history
SETTINGS_KEY_MAX_HISTORY = "clipboard-max-history"


class ClipboardEntry:
    """A single clipboard entry."""

    def __init__(self, text, timestamp=None, is_image=False, pinned=False):
        self.text = text
        self.timestamp = timestamp or time.time()
        self.is_image = is_image
        self.pinned = pinned

    def get_display_text(self, max_length=80):
        """Get truncated display text."""
        if not self.text:
            return "(empty)"
        text = self.text.replace('\n', ' ').replace('\r', ' ')
        if len(text) > max_length:
            return text[:max_length] + "..."
        return text

    def get_age_text(self):
        """Get human-readable age string."""
        elapsed = time.time() - self.timestamp
        if elapsed < 60:
            return "just now"
        elif elapsed < 3600:
            minutes = int(elapsed / 60)
            return "{}m ago".format(minutes)
        elif elapsed < 86400:
            hours = int(elapsed / 3600)
            return "{}h ago".format(hours)
        else:
            days = int(elapsed / 86400)
            return "{}d ago".format(days)

    def to_dict(self):
        """Serialize to dictionary."""
        return {
            "text": self.text,
            "timestamp": self.timestamp,
            "is_image": self.is_image,
            "pinned": self.pinned,
        }

    @classmethod
    def from_dict(cls, d):
        """Deserialize from dictionary."""
        return cls(
            text=d.get("text", ""),
            timestamp=d.get("timestamp", 0),
            is_image=d.get("is_image", False),
            pinned=d.get("pinned", False),
        )


class ClipboardManager:
    """
    Manages clipboard history for the on-screen keyboard.

    Features:
    - Copy, Cut, Paste, Select All actions
    - Configurable clipboard history (default 100, adjustable 10-1000)
    - Pin frequently used items to protect from deletion
    - Pinned items unlimited, history items auto-rotated
    - Persist history to disk across sessions
    - Settings panel for capacity management
    """

    def __init__(self):
        self._history = []
        self._pinned = []
        self._max_history = self._load_max_history_setting()
        self._clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
        self._primary = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY)
        self._on_change_callbacks = []
        self._on_settings_callbacks = []

        # Load persisted history
        self._load_history()

        # Monitor clipboard changes
        self._clipboard.connect("owner-change",
                                self._on_clipboard_owner_change)
        self._last_clipboard_text = self._get_clipboard_text()

    def connect(self, signal, callback):
        """Connect to signals: 'changed', 'settings-changed'."""
        if signal == "changed":
            self._on_change_callbacks.append(callback)
        elif signal == "settings-changed":
            self._on_settings_callbacks.append(callback)

    # ---- Settings ----

    def get_max_history(self):
        """Get the current maximum history capacity."""
        return self._max_history

    def set_max_history(self, value):
        """
        Set the maximum history capacity.
        Value is clamped between MIN_HISTORY_LIMIT and MAX_HISTORY_LIMIT.
        """
        old_value = self._max_history
        self._max_history = max(MIN_HISTORY_LIMIT,
                                min(MAX_HISTORY_LIMIT, int(value)))

        if self._max_history != old_value:
            self._save_max_history_setting()
            self._trim_history()
            self._save_history()
            self._notify_settings_changed()
            _logger.info("Clipboard max history set to {}".format(
                self._max_history))

    def get_pinned_count(self):
        """Get the number of pinned items."""
        return len(self._pinned)

    def get_history_count(self):
        """Get the number of unpinned history items."""
        return len(self._history)

    def get_total_count(self):
        """Get total count of all items (pinned + history)."""
        return len(self._pinned) + len(self._history)

    def get_capacity_info(self):
        """Get a dict with capacity information."""
        return {
            "max_history": self._max_history,
            "pinned_count": len(self._pinned),
            "history_count": len(self._history),
            "total_count": self.get_total_count(),
            "remaining": max(0, self._max_history - len(self._history)),
        }

    def _load_max_history_setting(self):
        """Load max history from GSettings."""
        try:
            settings = config.get_gsettings()
            if settings:
                value = settings.get_int(SETTINGS_KEY_MAX_HISTORY)
                if value >= MIN_HISTORY_LIMIT:
                    return min(MAX_HISTORY_LIMIT, value)
        except Exception:
            pass
        return DEFAULT_MAX_HISTORY

    def _save_max_history_setting(self):
        """Save max history to GSettings."""
        try:
            settings = config.get_gsettings()
            if settings:
                settings.set_int(SETTINGS_KEY_MAX_HISTORY, self._max_history)
        except Exception as e:
            _logger.warning("Failed to save max history setting: {}".format(e))

    def _trim_history(self):
        """Trim history to fit within max_history capacity."""
        if len(self._history) > self._max_history:
            self._history = self._history[:self._max_history]

    def _notify_settings_changed(self):
        """Notify callbacks of settings change."""
        for cb in self._on_settings_callbacks:
            try:
                cb(self)
            except Exception as e:
                _logger.warning("Settings callback error: {}".format(e))

    # ---- Clipboard Monitoring ----

    def _on_clipboard_owner_change(self, clipboard, event):
        """Called when clipboard content changes externally."""
        text = self._get_clipboard_text()
        if text and text != self._last_clipboard_text:
            self._last_clipboard_text = text
            self.add_entry(text)
            self._notify_change()

    def _notify_change(self):
        """Notify all callbacks of clipboard change."""
        for cb in self._on_change_callbacks:
            try:
                cb(self)
            except Exception as e:
                _logger.warning("Clipboard change callback error: {}".format(e))

    # ---- Entry Management ----

    def add_entry(self, text):
        """Add a text entry to clipboard history."""
        if not text or not text.strip():
            return

        # Remove duplicate from history if exists
        self._history = [e for e in self._history if e.text != text]

        # Also check pinned - don't duplicate
        for p in self._pinned:
            if p.text == text:
                return

        # Add new entry at the beginning
        entry = ClipboardEntry(text)
        self._history.insert(0, entry)

        # Trim to max size
        self._trim_history()

        # Save to disk
        self._save_history()

    def get_history(self):
        """Get all clipboard entries: pinned first, then history."""
        return list(self._pinned) + list(self._history)

    def get_pinned(self):
        """Get pinned entries."""
        return list(self._pinned)

    def get_unpinned(self):
        """Get unpinned history entries."""
        return list(self._history)

    def pin_entry(self, entry):
        """Pin an entry so it's protected from deletion and always available."""
        if entry in self._pinned:
            return

        self._pinned.append(entry)

        # Remove from history if present
        if entry in self._history:
            self._history.remove(entry)

        entry.pinned = True
        self._save_history()
        _logger.info("Entry pinned: '{}'".format(
            entry.get_display_text(30)))

    def unpin_entry(self, entry):
        """Unpin an entry (moves it back to history)."""
        if entry not in self._pinned:
            return

        self._pinned.remove(entry)
        entry.pinned = False

        # Add back to beginning of history
        self._history.insert(0, entry)

        # Trim if needed
        self._trim_history()

        self._save_history()
        _logger.info("Entry unpinned: '{}'".format(
            entry.get_display_text(30)))

    def remove_entry(self, entry):
        """Remove an entry from history or pinned list."""
        if entry in self._history:
            self._history.remove(entry)
        if entry in self._pinned:
            self._pinned.remove(entry)
        self._save_history()

    def clear_history(self):
        """Clear all unpinned history (pinned items are preserved)."""
        count = len(self._history)
        self._history.clear()
        self._save_history()
        _logger.info("Clipboard history cleared ({} items removed, "
                     "{} pinned kept)".format(count, len(self._pinned)))

    def clear_all(self):
        """Clear everything including pinned items."""
        h_count = len(self._history)
        p_count = len(self._pinned)
        self._history.clear()
        self._pinned.clear()
        self._save_history()
        _logger.info("Clipboard fully cleared ({} history + "
                     "{} pinned removed)".format(h_count, p_count))

    def paste_entry(self, entry):
        """Set clipboard to entry text for pasting."""
        self._clipboard.set_text(entry.text, -1)
        self._last_clipboard_text = entry.text

    # ---- Clipboard Actions ----

    def copy(self, text=None):
        """Copy text to clipboard and add to history."""
        if text:
            self._clipboard.set_text(text, -1)
            self._last_clipboard_text = text
            self.add_entry(text)

    def cut(self, text=None):
        """Cut text (copy to clipboard)."""
        if text:
            self.copy(text)

    def paste(self):
        """Get text from clipboard."""
        return self._get_clipboard_text()

    def select_all(self):
        """Send Ctrl+A to focused widget."""
        pass

    def get_clipboard_text(self):
        """Public accessor for clipboard text."""
        return self._get_clipboard_text()

    def _get_clipboard_text(self):
        """Get current clipboard text content."""
        try:
            text = self._clipboard.wait_for_text()
            return text if text else ""
        except Exception:
            return ""

    # ---- Search ----

    def search(self, query):
        """Search clipboard entries by text content."""
        if not query:
            return self.get_history()

        query = query.lower()
        results = []
        for entry in self.get_history():
            if query in entry.text.lower():
                results.append(entry)
        return results

    # ---- Persistence ----

    def _get_history_path(self):
        """Get path to clipboard history file."""
        user_dir = config.get_user_dir()
        return os.path.join(user_dir, CLIPBOARD_HISTORY_FILE)

    def _save_history(self):
        """Save clipboard history to disk."""
        try:
            data = {
                "version": 2,
                "max_history": self._max_history,
                "history": [e.to_dict() for e in self._history],
                "pinned": [e.to_dict() for e in self._pinned],
            }
            path = self._get_history_path()
            parent = os.path.dirname(path)
            if parent and not os.path.exists(parent):
                os.makedirs(parent, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            _logger.warning("Failed to save clipboard history: {}".format(e))

    def _load_history(self):
        """Load clipboard history from disk."""
        try:
            path = self._get_history_path()
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                # Load max_history from saved data if available
                saved_max = data.get("max_history")
                if saved_max and saved_max >= MIN_HISTORY_LIMIT:
                    self._max_history = min(MAX_HISTORY_LIMIT, saved_max)

                self._history = []
                for d in data.get("history", []):
                    entry = ClipboardEntry.from_dict(d)
                    entry.pinned = False
                    self._history.append(entry)

                self._pinned = []
                for d in data.get("pinned", []):
                    entry = ClipboardEntry.from_dict(d)
                    entry.pinned = True
                    self._pinned.append(entry)

                # Trim if loaded history exceeds current max
                self._trim_history()

                _logger.info("Clipboard loaded: {} history + "
                             "{} pinned (max={})".format(
                                 len(self._history), len(self._pinned),
                                 self._max_history))
        except Exception as e:
            _logger.warning("Failed to load clipboard history: {}".format(e))
            self._history = []
            self._pinned = []


class ClipboardPanel(Gtk.Box):
    """
    GTK panel displaying clipboard history with paste buttons.
    Shows as a popup/overlay on the keyboard.
    """

    def __init__(self, manager, on_paste_callback=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self._manager = manager
        self._on_paste = on_paste_callback
        self._buttons = []
        self._search_query = ""

        self.set_margin_start(6)
        self.set_margin_end(6)
        self.set_margin_top(4)
        self.set_margin_bottom(4)

        self._build_ui()
        self._refresh()

    def _build_ui(self):
        """Build the clipboard panel UI."""

        # ---- Header ----
        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        title = Gtk.Label(label="Clipboard")
        title.get_style_context().add_class("clipboard-title")
        header.pack_start(title, False, False, 0)

        # Count label
        self._count_label = Gtk.Label(label="")
        self._count_label.get_style_context().add_class("clipboard-count")
        header.pack_start(self._count_label, False, False, 8)

        # Clear button
        clear_btn = Gtk.Button(label="Clear All")
        clear_btn.get_style_context().add_class("clipboard-clear-btn")
        clear_btn.set_tooltip_text("Clear unpinned items")
        clear_btn.connect("clicked", self._on_clear_clicked)
        header.pack_end(clear_btn, False, False, 0)

        self.pack_start(header, False, False, 4)

        # ---- Search bar ----
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_placeholder_text("Search clipboard...")
        self._search_entry.connect("search-changed",
                                   self._on_search_changed)
        search_box.pack_start(self._search_entry, True, True, 0)
        self.pack_start(search_box, False, False, 2)

        # ---- Settings bar ----
        settings_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL,
                               spacing=4)
        settings_label = Gtk.Label(label="Capacity:")
        settings_label.get_style_context().add_class("clipboard-settings-label")
        settings_box.pack_start(settings_label, False, False, 0)

        self._capacity_spin = Gtk.SpinButton.new_with_range(
            MIN_HISTORY_LIMIT, MAX_HISTORY_LIMIT, 10)
        self._capacity_spin.set_value(self._manager.get_max_history())
        self._capacity_spin.set_tooltip_text(
            "Maximum number of history items (10-1000)")
        self._capacity_spin.connect("value-changed",
                                    self._on_capacity_changed)
        settings_box.pack_start(self._capacity_spin, False, False, 0)

        self._capacity_info = Gtk.Label(label="")
        self._capacity_info.get_style_context().add_class(
            "clipboard-capacity-info")
        settings_box.pack_start(self._capacity_info, False, False, 8)

        self.pack_start(settings_box, False, False, 2)

        # ---- Scrolled list ----
        self._scroll = Gtk.ScrolledWindow()
        self._scroll.set_policy(Gtk.PolicyType.NEVER,
                                Gtk.PolicyType.AUTOMATIC)
        self._scroll.set_min_content_height(150)
        self._scroll.set_max_content_height(400)

        self._list_box = Gtk.ListBox()
        self._list_box.set_selection_mode(Gtk.SelectionMode.NONE)
        self._scroll.add(self._list_box)
        self.pack_start(self._scroll, True, True, 0)

        self._update_capacity_info()

    def _on_search_changed(self, entry):
        """Handle search text change."""
        self._search_query = entry.get_text().strip()
        self._refresh()

    def _on_capacity_changed(self, spin_button):
        """Handle capacity spinner value change."""
        new_max = int(spin_button.get_value())
        self._manager.set_max_history(new_max)
        self._update_capacity_info()
        self._refresh()

    def _update_capacity_info(self):
        """Update the capacity information label."""
        info = self._manager.get_capacity_info()
        self._capacity_info.set_text(
            "{}/{} used, {} pinned".format(
                info["history_count"],
                info["max_history"],
                info["pinned_count"]))
        self._count_label.set_text("({} items)".format(info["total_count"]))

    def _refresh(self):
        """Refresh the clipboard list."""
        # Clear existing children
        for child in self._list_box.get_children():
            self._list_box.remove(child)
        self._buttons.clear()

        # Get entries (search or full)
        if self._search_query:
            entries = self._manager.search(self._search_query)
        else:
            entries = self._manager.get_history()

        if not entries:
            empty_label = Gtk.Label(
                label="Clipboard is empty" if not self._search_query
                else "No matching entries")
            empty_label.get_style_context().add_class("clipboard-empty")
            self._list_box.add(empty_label)
        else:
            for entry in entries:
                row = self._create_row(entry)
                self._list_box.add(row)

        self._list_box.show_all()
        self._update_capacity_info()

    def _create_row(self, entry):
        """Create a row widget for a clipboard entry."""
        row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)

        is_pinned = entry in self._manager.get_pinned()

        # Pin indicator
        pin_text = "📌" if is_pinned else "  "
        pin_label = Gtk.Label(label=pin_text)
        pin_label.set_size_request(24, -1)
        row.pack_start(pin_label, False, False, 0)

        # Text content
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=1)
        text_label = Gtk.Label(
            label=entry.get_display_text(80),
            xalign=0,
        )
        text_label.set_ellipsize(Pango.EllipsizeMode.END)
        text_label.get_style_context().add_class("clipboard-entry-text")
        content_box.pack_start(text_label, False, False, 0)

        age_label = Gtk.Label(label=entry.get_age_text(), xalign=0)
        age_label.get_style_context().add_class("clipboard-entry-age")
        content_box.pack_start(age_label, False, False, 0)
        row.pack_start(content_box, True, True, 0)

        # Paste button
        paste_btn = Gtk.Button(label="Paste")
        paste_btn.get_style_context().add_class("clipboard-paste-btn")
        paste_btn.set_tooltip_text("Copy to clipboard and paste")
        paste_btn.connect("clicked", self._on_paste_clicked, entry)
        row.pack_start(paste_btn, False, False, 0)

        # Pin/Unpin button
        pin_btn_label = "Unpin" if is_pinned else "Pin"
        pin_btn = Gtk.Button(label=pin_btn_label)
        pin_btn.get_style_context().add_class("clipboard-pin-btn")
        if is_pinned:
            pin_btn.set_tooltip_text(
                "Unpin (will move to history, subject to capacity)")
        else:
            pin_btn.set_tooltip_text(
                "Pin (protected from deletion and capacity limits)")
        pin_btn.connect("clicked", self._on_pin_clicked, entry)
        row.pack_start(pin_btn, False, False, 0)

        # Delete button
        del_btn = Gtk.Button(label="×")
        del_btn.get_style_context().add_class("clipboard-del-btn")
        del_btn.set_size_request(28, -1)
        if is_pinned:
            del_btn.set_tooltip_text("Delete pinned entry")
        else:
            del_btn.set_tooltip_text("Delete from history")
        del_btn.connect("clicked", self._on_delete_clicked, entry)
        row.pack_start(del_btn, False, False, 0)

        self._buttons.append(row)
        return row

    def _on_paste_clicked(self, button, entry):
        """Handle paste button click."""
        self._manager.paste_entry(entry)
        if self._on_paste:
            self._on_paste(entry.text)

    def _on_pin_clicked(self, button, entry):
        """Handle pin/unpin button click."""
        if entry in self._manager.get_pinned():
            self._manager.unpin_entry(entry)
        else:
            self._manager.pin_entry(entry)
        self._refresh()

    def _on_delete_clicked(self, button, entry):
        """Handle delete button click."""
        self._manager.remove_entry(entry)
        self._refresh()

    def _on_clear_clicked(self, button):
        """Handle clear all button click (preserves pinned)."""
        self._manager.clear_history()
        self._refresh()

    def update(self):
        """Public refresh method."""
        self._refresh()
