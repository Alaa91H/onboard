# -*- coding: utf-8 -*-

"""
Language Switcher for Onboard
Provides professional language switching with a quick-toggle button
and full language menu for the floating keyboard.

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

import os

from Onboard.Version import require_gi_versions
require_gi_versions()
from gi.repository import GLib, Gdk, Gtk, Pango

### Logging ###
import logging
_logger = logging.getLogger("LanguageSwitcher")
###############

### Config Singleton ###
from Onboard.Config import Config
config = Config()
########################


# Supported languages with their layout info
# Languages using system XKB layouts (no custom layout file needed)
# use_system_layout=True means the keyboard maps via XKB
SUPPORTED_LANGUAGES = {
    "en": {
        "name": "English",
        "native_name": "English",
        "layout_file": "Win11-Floating.onboard",
        "icon": "EN",
        "direction": "ltr",
        "code": "en",
        "use_system_layout": True,
    },
    "ar": {
        "name": "Arabic",
        "native_name": "\u0627\u0644\u0639\u0631\u0628\u064a\u0629",
        "layout_file": "Win11-Arabic.onboard",
        "icon": "\u0639\u0631\u0628",
        "direction": "rtl",
        "code": "ar",
        "use_system_layout": False,
    },
    "fr": {
        "name": "French",
        "native_name": "Fran\u00e7ais",
        "layout_file": None,
        "icon": "FR",
        "direction": "ltr",
        "code": "fr",
        "use_system_layout": True,
    },
    "de": {
        "name": "German",
        "native_name": "Deutsch",
        "layout_file": None,
        "icon": "DE",
        "direction": "ltr",
        "code": "de",
        "use_system_layout": True,
    },
    "es": {
        "name": "Spanish",
        "native_name": "Espa\u00f1ol",
        "layout_file": None,
        "icon": "ES",
        "direction": "ltr",
        "code": "es",
        "use_system_layout": True,
    },
    "pt": {
        "name": "Portuguese",
        "native_name": "Portugu\u00eas",
        "layout_file": None,
        "icon": "PT",
        "direction": "ltr",
        "code": "pt",
        "use_system_layout": True,
    },
    "it": {
        "name": "Italian",
        "native_name": "Italiano",
        "layout_file": None,
        "icon": "IT",
        "direction": "ltr",
        "code": "it",
        "use_system_layout": True,
    },
    "nl": {
        "name": "Dutch",
        "native_name": "Nederlands",
        "layout_file": None,
        "icon": "NL",
        "direction": "ltr",
        "code": "nl",
        "use_system_layout": True,
    },
    "ru": {
        "name": "Russian",
        "native_name": "\u0420\u0443\u0441\u0441\u043a\u0438\u0439",
        "layout_file": None,
        "icon": "\u0420\u0423",
        "direction": "ltr",
        "code": "ru",
        "use_system_layout": True,
    },
    "uk": {
        "name": "Ukrainian",
        "native_name": "\u0423\u043a\u0440\u0430\u0457\u043d\u0441\u044c\u043a\u0430",
        "layout_file": None,
        "icon": "\u0423\u041a",
        "direction": "ltr",
        "code": "uk",
        "use_system_layout": True,
    },
    "zh": {
        "name": "Chinese",
        "native_name": "\u4e2d\u6587",
        "layout_file": None,
        "icon": "\u4e2d",
        "direction": "ltr",
        "code": "zh",
        "use_system_layout": True,
    },
    "ja": {
        "name": "Japanese",
        "native_name": "\u65e5\u672c\u8a9e",
        "layout_file": None,
        "icon": "\u65e5",
        "direction": "ltr",
        "code": "ja",
        "use_system_layout": True,
    },
    "ko": {
        "name": "Korean",
        "native_name": "\ud55c\uad6d\uc5b4",
        "layout_file": None,
        "icon": "\ud55c",
        "direction": "ltr",
        "code": "ko",
        "use_system_layout": True,
    },
    "he": {
        "name": "Hebrew",
        "native_name": "\u05e2\u05d1\u05e8\u05d9\u05ea",
        "layout_file": None,
        "icon": "\u05e2\u05d1",
        "direction": "rtl",
        "code": "he",
        "use_system_layout": True,
    },
    "fa": {
        "name": "Persian",
        "native_name": "\u0641\u0627\u0631\u0633\u06cc",
        "layout_file": None,
        "icon": "\u0641\u0627",
        "direction": "rtl",
        "code": "fa",
        "use_system_layout": True,
    },
    "ur": {
        "name": "Urdu",
        "native_name": "\u0627\u0631\u062f\u0648",
        "layout_file": None,
        "icon": "\u0627\u0631\u062f",
        "direction": "rtl",
        "code": "ur",
        "use_system_layout": True,
    },
    "hi": {
        "name": "Hindi",
        "native_name": "\u0939\u093f\u0928\u094d\u0926\u0940",
        "layout_file": None,
        "icon": "\u0939\u093f",
        "direction": "ltr",
        "code": "hi",
        "use_system_layout": True,
    },
    "tr": {
        "name": "Turkish",
        "native_name": "T\u00fcrk\u00e7e",
        "layout_file": None,
        "icon": "TR",
        "direction": "ltr",
        "code": "tr",
        "use_system_layout": True,
    },
    "pl": {
        "name": "Polish",
        "native_name": "Polski",
        "layout_file": None,
        "icon": "PL",
        "direction": "ltr",
        "code": "pl",
        "use_system_layout": True,
    },
    "sv": {
        "name": "Swedish",
        "native_name": "Svenska",
        "layout_file": None,
        "icon": "SV",
        "direction": "ltr",
        "code": "sv",
        "use_system_layout": True,
    },
    "da": {
        "name": "Danish",
        "native_name": "Dansk",
        "layout_file": None,
        "icon": "DA",
        "direction": "ltr",
        "code": "da",
        "use_system_layout": True,
    },
    "no": {
        "name": "Norwegian",
        "native_name": "Norsk",
        "layout_file": None,
        "icon": "NO",
        "direction": "ltr",
        "code": "no",
        "use_system_layout": True,
    },
    "fi": {
        "name": "Finnish",
        "native_name": "Suomi",
        "layout_file": None,
        "icon": "FI",
        "direction": "ltr",
        "code": "fi",
        "use_system_layout": True,
    },
    "cs": {
        "name": "Czech",
        "native_name": "\u010ce\u0161tina",
        "layout_file": None,
        "icon": "CS",
        "direction": "ltr",
        "code": "cs",
        "use_system_layout": True,
    },
    "ro": {
        "name": "Romanian",
        "native_name": "Rom\u00e2n\u0103",
        "layout_file": None,
        "icon": "RO",
        "direction": "ltr",
        "code": "ro",
        "use_system_layout": True,
    },
    "hu": {
        "name": "Hungarian",
        "native_name": "Magyar",
        "layout_file": None,
        "icon": "HU",
        "direction": "ltr",
        "code": "hu",
        "use_system_layout": True,
    },
    "el": {
        "name": "Greek",
        "native_name": "\u0395\u03bb\u03bb\u03b7\u03bd\u03b9\u03ba\u03ac",
        "layout_file": None,
        "icon": "\u0395\u039b",
        "direction": "ltr",
        "code": "el",
        "use_system_layout": True,
    },
    "th": {
        "name": "Thai",
        "native_name": "\u0e44\u0e17\u0e22",
        "layout_file": None,
        "icon": "\u0e44\u0e17",
        "direction": "ltr",
        "code": "th",
        "use_system_layout": True,
    },
    "vi": {
        "name": "Vietnamese",
        "native_name": "Ti\u1ebfng Vi\u1ec7t",
        "layout_file": None,
        "icon": "VI",
        "direction": "ltr",
        "code": "vi",
        "use_system_layout": True,
    },
    "id": {
        "name": "Indonesian",
        "native_name": "Bahasa Indonesia",
        "layout_file": None,
        "icon": "ID",
        "direction": "ltr",
        "code": "id",
        "use_system_layout": True,
    },
    "ms": {
        "name": "Malay",
        "native_name": "Bahasa Melayu",
        "layout_file": None,
        "icon": "MS",
        "direction": "ltr",
        "code": "ms",
        "use_system_layout": True,
    },
    "bn": {
        "name": "Bengali",
        "native_name": "\u09ac\u09be\u0982\u09b2\u09be",
        "layout_file": None,
        "icon": "\u09ac\u09be",
        "direction": "ltr",
        "code": "bn",
        "use_system_layout": True,
    },
    "sw": {
        "name": "Swahili",
        "native_name": "Kiswahili",
        "layout_file": None,
        "icon": "SW",
        "direction": "ltr",
        "code": "sw",
        "use_system_layout": True,
    },
    "kn": {
        "name": "Kannada",
        "native_name": "\u0c95\u0ca8\u0ccd0ca1",
        "layout_file": None,
        "icon": "\u0c95\u0ca8",
        "direction": "ltr",
        "code": "kn",
        "use_system_layout": True,
    },
    "ta": {
        "name": "Tamil",
        "native_name": "\u0ba4\u0bae\u0bbf\u0bb4\u0bcd",
        "layout_file": None,
        "icon": "\u0ba4\u0bae",
        "direction": "ltr",
        "code": "ta",
        "use_system_layout": True,
    },
    "te": {
        "name": "Telugu",
        "native_name": "\u0c24\u0c46\u0c32\u0c41\u0c17\u0c41",
        "layout_file": None,
        "icon": "\u0c24\u0c46",
        "direction": "ltr",
        "code": "te",
        "use_system_layout": True,
    },
    "ml": {
        "name": "Malayalam",
        "native_name": "\u0d2e\u0d32\u0d2f\u0d3e\u0d33\u0d02",
        "layout_file": None,
        "icon": "\u0d2e\u0d32",
        "direction": "ltr",
        "code": "ml",
        "use_system_layout": True,
    },
    "mr": {
        "name": "Marathi",
        "native_name": "\u092e\u0930\u093e\u0920\u0940",
        "layout_file": None,
        "icon": "\u092e\u0930",
        "direction": "ltr",
        "code": "mr",
        "use_system_layout": True,
    },
    "gu": {
        "name": "Gujarati",
        "native_name": "\u0a97\u0ac1\u0a9c\u0ab0\u0abe\u0a9f\u0ac0",
        "layout_file": None,
        "icon": "\u0a97\u0ac1",
        "direction": "ltr",
        "code": "gu",
        "use_system_layout": True,
    },
    "pa": {
        "name": "Punjabi",
        "native_name": "\u0a2a\u0a70\u0a1c\u0a3e\u0a2c\u0a40",
        "layout_file": None,
        "icon": "\u0a2a\u0a70",
        "direction": "ltr",
        "code": "pa",
        "use_system_layout": True,
    },
}


class LanguageInfo:
    """Represents a language configuration."""

    def __init__(self, lang_id, data):
        self.id = lang_id
        self.name = data["name"]
        self.native_name = data["native_name"]
        self.layout_file = data.get("layout_file")
        self.icon = data["icon"]
        self.direction = data.get("direction", "ltr")
        self.code = data.get("code", lang_id)

    def get_display_name(self):
        """Get display name for menu."""
        return "{} ({})".format(self.name, self.native_name)

    def get_short_label(self):
        """Get short label for toggle button."""
        return self.icon


class LanguageSwitcher:
    """
    Manages language switching for the on-screen keyboard.

    Features:
    - Quick toggle between last two languages (via button)
    - Full language menu (via long-press or menu button)
    - Remembers last used languages per application
    - Supports RTL layout switching (Arabic)
    """

    def __init__(self):
        self._languages = {}
        self._current_lang = "en"
        self._previous_lang = None
        self._enabled_languages = ["en", "ar"]  # Default enabled
        self._on_language_changed_callbacks = []

        # Load all supported languages
        for lang_id, data in SUPPORTED_LANGUAGES.items():
            self._languages[lang_id] = LanguageInfo(lang_id, data)

        # Restore last language from config
        self._restore_language()

    def connect(self, signal, callback):
        """Connect to language change signals."""
        if signal == "language-changed":
            self._on_language_changed_callbacks.append(callback)

    def get_current_language(self):
        """Get current language info."""
        return self._languages.get(self._current_lang)

    def get_current_lang_id(self):
        """Get current language ID."""
        return self._current_lang

    def get_previous_language(self):
        """Get previous language info."""
        if self._previous_lang:
            return self._languages.get(self._previous_lang)
        return None

    def get_enabled_languages(self):
        """Get list of enabled language info objects."""
        return [self._languages[lang_id]
                for lang_id in self._enabled_languages
                if lang_id in self._languages]

    def get_all_languages(self):
        """Get all available languages."""
        return list(self._languages.values())

    def set_current_language(self, lang_id):
        """Set the current language."""
        if lang_id not in self._languages:
            _logger.warning("Unknown language: {}".format(lang_id))
            return

        if lang_id == self._current_lang:
            return

        self._previous_lang = self._current_lang
        self._current_lang = lang_id

        _logger.info("Language changed: {} -> {}".format(
            self._previous_lang, self._current_lang))

        # Save to config
        self._save_language()

        # Notify callbacks
        self._notify_language_changed()

    def toggle_language(self):
        """Toggle between current and previous language."""
        if self._previous_lang and self._previous_lang in self._languages:
            old = self._current_lang
            self._current_lang = self._previous_lang
            self._previous_lang = old
            self._save_language()
            self._notify_language_changed()
        elif len(self._enabled_languages) >= 2:
            # Toggle between first two enabled languages
            current_idx = 0
            if self._current_lang in self._enabled_languages:
                current_idx = self._enabled_languages.index(self._current_lang)
            next_idx = (current_idx + 1) % len(self._enabled_languages)
            self._previous_lang = self._current_lang
            self._current_lang = self._enabled_languages[next_idx]
            self._save_language()
            self._notify_language_changed()

    def cycle_next_language(self):
        """Cycle to next language in the enabled list."""
        if not self._enabled_languages:
            return

        current_idx = 0
        if self._current_lang in self._enabled_languages:
            current_idx = self._enabled_languages.index(self._current_lang)
        next_idx = (current_idx + 1) % len(self._enabled_languages)

        self._previous_lang = self._current_lang
        self._current_lang = self._enabled_languages[next_idx]
        self._save_language()
        self._notify_language_changed()

    def enable_language(self, lang_id):
        """Add a language to the enabled list."""
        if lang_id in self._languages and lang_id not in self._enabled_languages:
            self._enabled_languages.append(lang_id)

    def disable_language(self, lang_id):
        """Remove a language from the enabled list."""
        if lang_id in self._enabled_languages:
            self._enabled_languages.remove(lang_id)

    def is_rtl(self):
        """Check if current language is right-to-left."""
        lang = self.get_current_language()
        return lang and lang.direction == "rtl"

    def get_layout_file(self):
        """Get layout file for current language."""
        lang = self.get_current_language()
        if lang and lang.layout_file:
            return lang.layout_file
        return None  # Use default layout

    def _notify_language_changed(self):
        """Notify all callbacks of language change."""
        lang = self.get_current_language()
        for cb in self._on_language_changed_callbacks:
            try:
                cb(lang)
            except Exception as e:
                _logger.warning("Language change callback error: {}".format(e))

    def _save_language(self):
        """Save current language to config."""
        try:
            config.keyboard.set_string("current-layout",
                                       self.get_layout_file() or "")
        except Exception as e:
            _logger.warning("Failed to save language: {}".format(e))

    def _restore_language(self):
        """Restore language from config."""
        try:
            layout = config.keyboard.get_string("current-layout")
            for lang_id, lang in self._languages.items():
                if lang.layout_file == layout:
                    self._current_lang = lang_id
                    break
        except Exception:
            pass


class LanguageSwitcherWidget(Gtk.Box):
    """
    GTK widget for language switching.
    Shows a toggle button that switches between languages,
    and a menu for selecting from all enabled languages.
    """

    def __init__(self, switcher, on_language_changed=None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self._switcher = switcher
        self._on_language_changed = on_language_changed

        self.set_margin_start(2)
        self.set_margin_end(2)
        self.set_margin_top(2)
        self.set_margin_bottom(2)

        self._build_ui()

        # Connect to switcher signals
        self._switcher.connect("language-changed", self._on_lang_changed)

    def _build_ui(self):
        """Build the language switcher UI."""

        # Quick toggle button (shows current language)
        self._toggle_btn = Gtk.Button()
        self._toggle_btn.get_style_context().add_class("lang-toggle-btn")
        self._toggle_btn.set_tooltip_text("Switch language (click) / Show all (right-click)")
        self._toggle_btn.connect("clicked", self._on_toggle_clicked)
        self._toggle_btn.connect("button-press-event", self._on_button_press)
        self.pack_start(self._toggle_btn, True, True, 0)

        self._update_toggle_label()

    def _update_toggle_label(self):
        """Update the toggle button label."""
        lang = self._switcher.get_current_language()
        if lang:
            self._toggle_btn.set_label(lang.get_short_label())
            self._toggle_btn.set_tooltip_text(
                "Current: {} - Click to switch".format(lang.get_display_name()))
        else:
            self._toggle_btn.set_label("EN")

    def _on_toggle_clicked(self, button):
        """Handle toggle button click - cycle to next language."""
        self._switcher.cycle_next_language()

    def _on_button_press(self, button, event):
        """Handle right-click to show language menu."""
        if event.button == 3:  # Right click
            self._show_language_menu()
            return True
        return False

    def _show_language_menu(self):
        """Show popup menu with all enabled languages."""
        menu = Gtk.Menu()

        for lang in self._switcher.get_enabled_languages():
            item = Gtk.MenuItem(label=lang.get_display_name())
            is_current = (lang.id == self._switcher.get_current_lang_id())
            if is_current:
                item.set_label("✓ " + lang.get_display_name())
            item.connect("activate", self._on_menu_item_activated, lang.id)
            menu.append(item)

        menu.append(Gtk.SeparatorMenuItem())

        # Settings item
        settings_item = Gtk.MenuItem(label="Language Settings...")
        settings_item.connect("activate", self._on_settings_clicked)
        menu.append(settings_item)

        menu.show_all()
        menu.popup_at_widget(self._toggle_btn, Gtk.Gravity.SOUTH,
                             Gtk.Gravity.NORTH, None)

    def _on_menu_item_activated(self, item, lang_id):
        """Handle language menu item selection."""
        self._switcher.set_current_language(lang_id)

    def _on_settings_clicked(self, item):
        """Handle settings menu item."""
        # Open Onboard settings to language page
        _logger.info("Language settings requested")

    def _on_lang_changed(self, switcher, lang):
        """Handle language change from switcher."""
        self._update_toggle_label()
        if self._on_language_changed:
            self._on_language_changed(lang)
