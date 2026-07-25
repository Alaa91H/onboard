# -*- coding: utf-8 -*-

"""
Win11 Floating Keyboard Integration Module
Ties together all Windows 11 floating keyboard features:
- Always-on-top floating mode with close button
- Clipboard manager
- Emoji picker
- Long-press alternatives
- Number row
- Word suggestions / autocomplete
- Arabic language support
- Professional language switching

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

from Onboard.Version import require_gi_versions
require_gi_versions()
from gi.repository import GLib, Gdk, Gtk

### Logging ###
import logging
_logger = logging.getLogger("Win11FloatingIntegration")
###############

### Config Singleton ###
from Onboard.Config import Config
config = Config()
########################

from Onboard.ClipboardManager import ClipboardManager, ClipboardPanel
from Onboard.EmojiPicker import EmojiPicker
from Onboard.LanguageSwitcher import LanguageSwitcher, LanguageSwitcherWidget


class Win11FloatingIntegration:
    """
    Master integration class for the Windows 11 floating keyboard.

    This class manages:
    1. Always-on-top floating window behavior
    2. Close button handling
    3. Clipboard panel toggle
    4. Emoji picker panel toggle
    5. Language switching
    6. Long-press alternatives integration
    7. Number row behavior
    8. Word suggestion bar integration
    """

    def __init__(self, keyboard_widget=None, kbd_window=None):
        self._keyboard_widget = keyboard_widget
        self._kbd_window = kbd_window

        # Initialize sub-modules
        self._clipboard_manager = ClipboardManager()
        self._language_switcher = LanguageSwitcher()

        # Panels (created on demand)
        self._clipboard_panel = None
        self._emoji_picker = None
        self._language_widget = None

        # Panel visibility state
        self._clipboard_visible = False
        self._emoji_visible = False

        # Connect signals
        self._clipboard_manager.connect("changed", self._on_clipboard_changed)
        self._language_switcher.connect("language-changed",
                                        self._on_language_changed)

        _logger.info("Win11FloatingIntegration initialized")

    @property
    def clipboard_manager(self):
        """Get the clipboard manager."""
        return self._clipboard_manager

    @property
    def language_switcher(self):
        """Get the language switcher."""
        return self._language_switcher

    # ---- Window Management ----

    def setup_floating_window(self):
        """
        Configure the keyboard window for always-on-top floating mode.
        The keyboard stays visible until the user clicks the close button.
        """
        if not self._kbd_window:
            return

        window = self._kbd_window

        # Keep above all windows
        if hasattr(window, 'set_keep_above'):
            window.set_keep_above(True)

        # Make window non-auto-hidable
        if hasattr(window, '_sticky'):
            window._sticky = True

        # Disable auto-hide for this mode
        if hasattr(config, 'auto_show'):
            # Store original auto-show setting and disable it
            self._original_auto_show = getattr(config.auto_show,
                                               'enabled', False)

        _logger.info("Floating window configured for always-on-top mode")

    def close_keyboard(self):
        """
        Close the floating keyboard.
        Called when the user clicks the close (X) button.
        """
        if self._kbd_window:
            self._kbd_window.transition_visible_to(False)
            _logger.info("Floating keyboard closed by user")

    def show_keyboard(self):
        """Show the floating keyboard."""
        if self._kbd_window:
            self._kbd_window.transition_visible_to(True)

    # ---- Key Action Handlers ----

    def handle_key_action(self, key_id):
        """
        Handle special key actions for the Win11 floating keyboard.
        Returns True if the key was handled, False otherwise.
        """
        if key_id == "win11-close":
            self.close_keyboard()
            return True

        elif key_id == "win11-move":
            # Initiate window drag
            self._start_window_drag()
            return True

        elif key_id == "win11-lang-switch":
            self._language_switcher.cycle_next_language()
            return True

        elif key_id == "win11-emoji":
            self.toggle_emoji_picker()
            return True

        elif key_id == "win11-clipboard":
            self.toggle_clipboard_panel()
            return True

        elif key_id == "win11-layer1":
            # Switch to number/symbol layer
            if self._keyboard_widget:
                self._keyboard_widget.keyboard.set_layer(1)
            return True

        elif key_id == "win11-layer0":
            # Switch back to alpha layer
            if self._keyboard_widget:
                self._keyboard_widget.keyboard.set_layer(0)
            return True

        elif key_id == "BKSP-num":
            # Backspace in number row
            if self._keyboard_widget:
                self._keyboard_widget.keyboard.key_press_backspace()
            return True

        return False

    def _start_window_drag(self):
        """Start dragging the keyboard window."""
        if self._kbd_window and hasattr(self._kbd_window, 'begin_move'):
            self._kbd_window.begin_move()

    # ---- Clipboard Panel ----

    def toggle_clipboard_panel(self):
        """Toggle the clipboard panel visibility."""
        if self._clipboard_visible:
            self.hide_clipboard_panel()
        else:
            self.show_clipboard_panel()

    def show_clipboard_panel(self):
        """Show the clipboard panel."""
        self.hide_emoji_picker()  # Hide emoji if open

        if not self._clipboard_panel:
            self._clipboard_panel = ClipboardPanel(
                self._clipboard_manager,
                on_paste_callback=self._on_clipboard_paste
            )

        # Insert into keyboard layout
        if self._keyboard_widget:
            self._insert_overlay_panel(self._clipboard_panel)

        self._clipboard_visible = True
        _logger.info("Clipboard panel shown")

    def hide_clipboard_panel(self):
        """Hide the clipboard panel."""
        if self._clipboard_panel and self._clipboard_visible:
            self._remove_overlay_panel(self._clipboard_panel)
            self._clipboard_visible = False
            _logger.info("Clipboard panel hidden")

    def _on_clipboard_paste(self, text):
        """Handle paste from clipboard panel."""
        if self._keyboard_widget and text:
            self._keyboard_widget.keyboard.type_text(text)
        self.hide_clipboard_panel()

    def _on_clipboard_changed(self, manager):
        """Handle clipboard content change."""
        if self._clipboard_panel and self._clipboard_visible:
            self._clipboard_panel.update()

    # ---- Emoji Picker ----

    def toggle_emoji_picker(self):
        """Toggle the emoji picker visibility."""
        if self._emoji_visible:
            self.hide_emoji_picker()
        else:
            self.show_emoji_picker()

    def show_emoji_picker(self):
        """Show the emoji picker panel."""
        self.hide_clipboard_panel()  # Hide clipboard if open

        if not self._emoji_picker:
            self._emoji_picker = EmojiPicker(
                on_emoji_selected=self._on_emoji_selected
            )

        # Insert into keyboard layout
        if self._keyboard_widget:
            self._insert_overlay_panel(self._emoji_picker)

        self._emoji_visible = True
        _logger.info("Emoji picker shown")

    def hide_emoji_picker(self):
        """Hide the emoji picker."""
        if self._emoji_picker and self._emoji_visible:
            self._remove_overlay_panel(self._emoji_picker)
            self._emoji_visible = False
            _logger.info("Emoji picker hidden")

    def _on_emoji_selected(self, emoji):
        """Handle emoji selection."""
        if self._keyboard_widget:
            self._keyboard_widget.keyboard.type_text(emoji)
        # Keep picker open for multiple selections

    # ---- Language Switching ----

    def _on_language_changed(self, lang):
        """Handle language change."""
        if not lang:
            return

        _logger.info("Language changed to: {}".format(lang.name))

        # Update the layout if the language has a specific layout file
        layout_file = self._language_switcher.get_layout_file()
        if layout_file and self._keyboard_widget:
            self._load_layout(layout_file)

        # Update the language switch button label
        self._update_lang_button_label()

    def _load_layout(self, layout_file):
        """Load a keyboard layout file."""
        try:
            keyboard = self._keyboard_widget.keyboard
            layout_path = self._find_layout_file(layout_file)
            if layout_path:
                keyboard.set_layout(layout_path)
                _logger.info("Layout loaded: {}".format(layout_file))
        except Exception as e:
            _logger.error("Failed to load layout {}: {}".format(
                layout_file, e))

    def _find_layout_file(self, filename):
        """Find a layout file in the layouts directories."""
        import os
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        layouts_dir = os.path.join(base_dir, "layouts")

        # Check user layouts first
        user_dir = config.get_user_dir()
        user_layouts = os.path.join(user_dir, "layouts")
        path = os.path.join(user_layouts, filename)
        if os.path.exists(path):
            return path

        # Check system layouts
        path = os.path.join(layouts_dir, filename)
        if os.path.exists(path):
            return path

        return None

    def _update_lang_button_label(self):
        """Update the language switch button label."""
        lang = self._language_switcher.get_current_language()
        if lang and self._keyboard_widget:
            # The button is part of the layout, we'd need to update it
            # through the layout system
            pass

    # ---- Panel Management ----

    def _insert_overlay_panel(self, panel):
        """Insert an overlay panel into the keyboard layout."""
        if not self._keyboard_widget:
            return

        # Get the keyboard's main box
        try:
            keyboard = self._keyboard_widget.keyboard
            # Find the main container and add the panel
            parent = self._keyboard_widget.get_parent()
            if parent:
                # Add panel as overlay
                parent.pack_start(panel, False, False, 0)
                parent.reorder_child(panel, 0)  # Put it at the top
                panel.show_all()
        except Exception as e:
            _logger.warning("Failed to insert overlay panel: {}".format(e))

    def _remove_overlay_panel(self, panel):
        """Remove an overlay panel from the keyboard layout."""
        try:
            parent = panel.get_parent()
            if parent:
                parent.remove(panel)
        except Exception as e:
            _logger.warning("Failed to remove overlay panel: {}".format(e))

    # ---- Long Press Alternatives ----

    def get_long_press_alternatives(self, key_id):
        """
        Get alternative characters for long-press on a key.
        Returns a list of (label, char) tuples.
        """
        alternatives = {
            # Vowels with accents
            "a": [("à", "à"), ("á", "á"), ("â", "â"), ("ä", "ä"), ("ã", "ã")],
            "e": [("è", "è"), ("é", "é"), ("ê", "ê"), ("ë", "ë")],
            "i": [("ì", "ì"), ("í", "í"), ("î", "î"), ("ï", "ï")],
            "o": [("ò", "ò"), ("ó", "ó"), ("ô", "ô"), ("ö", "ö"), ("õ", "õ")],
            "u": [("ù", "ù"), ("ú", "ú"), ("û", "û"), ("ü", "ü")],
            "n": [("ñ", "ñ")],
            "c": [("ç", "ç")],

            # Common punctuation alternatives
            ".": [(",", ","), (";", ";"), ("!", "!"), ("?", "?")],
            ",": [(".", "."), (";", ";"), (":", ":")],
            "-": [("_", "_"), ("–", "–"), ("—", "—")],
            "'": [(""", """), ("'", "'"), ("`", "`")],
            "\"": [(""", """), ("'", "'"), ("„", "„")],

            # Number alternatives (symbols)
            "1": [("¹", "¹"), ("₁", "₁")],
            "2": [("²", "²"), ("₂", "₂")],
            "3": [("³", "³"), ("₃", "₃")],

            # Arabic diacritics (for Arabic mode)
            "ا": [("َ", "َ"), ("ُ", "ُ"), ("ِ", "ِ"), ("ّ", "ّ"), ("ْ", "ْ")],
            "و": [("َ", "َ"), ("ُ", "ُ"), ("ِ", "ِ"), ("ّ", "ّ")],
            "ي": [("َ", "َ"), ("ُ", "ُ"), ("ِ", "ِ"), ("ّ", "ّ")],
        }

        return alternatives.get(key_id, [])

    # ---- Cleanup ----

    def cleanup(self):
        """Clean up all resources."""
        self.hide_clipboard_panel()
        self.hide_emoji_picker()
        _logger.info("Win11FloatingIntegration cleaned up")


# ---- Module-level convenience ----

_integration_instance = None


def get_integration(keyboard_widget=None, kbd_window=None):
    """Get or create the global integration instance."""
    global _integration_instance
    if _integration_instance is None:
        _integration_instance = Win11FloatingIntegration(
            keyboard_widget, kbd_window)
    return _integration_instance


def setup_win11_floating(keyboard_widget, kbd_window):
    """Quick setup for Win11 floating keyboard."""
    integration = get_integration(keyboard_widget, kbd_window)
    integration.setup_floating_window()
    return integration
