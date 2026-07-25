# -*- coding: utf-8 -*-

"""
KeyboardWidget Win11 Integration Patch
Hooks into KeyboardWidget to handle Win11 floating keyboard features:
- Special key actions (close, emoji, clipboard, language switch)
- Long-press alternatives popup
- Number row key handling
- Panel overlay management

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
_logger = logging.getLogger("Win11KeyboardWidgetPatch")
###############

### Config Singleton ###
from Onboard.Config import Config
config = Config()
########################


# Win11 special key IDs that need custom handling
WIN11_SPECIAL_KEYS = frozenset([
    "win11-close",
    "win11-move",
    "win11-lang-switch",
    "win11-emoji",
    "win11-clipboard",
    "win11-layer0",
    "win11-layer1",
    "BKSP-num",
])


class Win11KeyboardWidgetPatch:
    """
    Patches KeyboardWidget to support Win11 floating keyboard features.
    """

    def __init__(self, keyboard_widget):
        self._widget = keyboard_widget
        self._integration = None
        self._long_press_alternatives = {}
        self._setup_complete = False

    def setup(self, integration):
        """
        Complete setup with the Win11 integration module.
        Call after both widget and integration are created.
        """
        self._integration = integration
        self._setup_long_press_alternatives()
        self._setup_complete = True
        _logger.info("Win11KeyboardWidgetPatch setup complete")

    def _setup_long_press_alternatives(self):
        """Pre-compute long press alternatives for common keys."""
        if not self._integration:
            return

        # Get alternatives from integration
        for key_id in ["a", "e", "i", "o", "u", "n", "c",
                       ".", ",", "-", "'", "\""]:
            alternatives = self._integration.get_long_press_alternatives(key_id)
            if alternatives:
                self._long_press_alternatives[key_id] = alternatives

    def handle_key_press(self, key_id, event=None):
        """
        Handle a key press event.
        Returns True if the key was handled (and should not be processed further).
        """
        if not self._integration:
            return False

        # Check if it's a Win11 special key
        if key_id in WIN11_SPECIAL_KEYS:
            return self._integration.handle_key_action(key_id)

        return False

    def handle_long_press(self, key_id):
        """
        Handle long press on a key.
        Shows alternatives popup for the key.
        Returns True if alternatives were shown.
        """
        if not self._integration:
            return False

        alternatives = self._integration.get_long_press_alternatives(key_id)
        if not alternatives:
            return False

        self._show_alternatives_popup(key_id, alternatives)
        return True

    def _show_alternatives_popup(self, key_id, alternatives):
        """
        Show a popup with alternative characters for long press.
        """
        popup = Gtk.Window(type=Gtk.WindowType.POPUP)
        popup.set_decorated(False)
        popup.set_skip_taskbar_hint(True)
        popup.set_skip_pager_hint(True)
        popup.set_keep_above(True)
        popup.set_accept_focus(False)
        popup.set_app_paintable(True)

        # Apply dark styling
        popup.set_name("win11-alternatives-popup")

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=2)
        box.set_margin_start(4)
        box.set_margin_end(4)
        box.set_margin_top(4)
        box.set_margin_bottom(4)

        for label, char in alternatives:
            btn = Gtk.Button(label=label)
            btn.set_size_request(40, 40)
            btn.get_style_context().add_class("win11-alt-btn")
            btn.connect("clicked", self._on_alternative_selected,
                        popup, char)
            box.pack_start(btn, False, False, 0)

        popup.add(box)

        # Position above the key (approximate)
        self._position_popup_near_keyboard(popup)

        popup.show_all()

        # Auto-close after timeout
        GLib.timeout_add(3000, self._close_popup, popup)

    def _on_alternative_selected(self, button, popup, char):
        """Handle alternative character selection."""
        popup.destroy()

        # Type the selected character
        if self._widget and hasattr(self._widget, 'keyboard'):
            self._widget.keyboard.type_text(char)

    def _close_popup(self, popup):
        """Close a popup window."""
        try:
            if popup.get_visible():
                popup.destroy()
        except Exception:
            pass
        return False  # Don't repeat

    def _position_popup_near_keyboard(self, popup):
        """Position a popup window near the keyboard."""
        if not self._widget:
            return

        try:
            # Get keyboard widget position
            alloc = self._widget.get_allocation()
            win = self._widget.get_window()
            if win:
                x, y = win.get_origin()
                popup.move(x + alloc.width // 2 - 100, y - 60)
        except Exception:
            # Default position
            popup.move(200, 200)


def patch_keyboard_widget(keyboard_widget):
    """
    Apply Win11 patches to a KeyboardWidget instance.
    Call this after KeyboardWidget is created.
    """
    patch = Win11KeyboardWidgetPatch(keyboard_widget)
    keyboard_widget._win11_patch = patch
    return patch


# ---- CSS Styling for Win11 Panels ----

WIN11_PANEL_CSS = """
/* Win11 Alternatives Popup */
#win11-alternatives-popup {
    background-color: #2D2D2D;
    border-radius: 8px;
    border: 1px solid #404040;
    box-shadow: 0 4px 12px rgba(0,0,0,0.5);
}

.win11-alt-btn {
    background-color: #3D3D3D;
    color: #FFFFFF;
    border-radius: 6px;
    border: none;
    padding: 4px 8px;
    font-size: 18px;
    min-width: 36px;
    min-height: 36px;
}

.win11-alt-btn:hover {
    background-color: #505050;
}

.win11-alt-btn:active {
    background-color: #0078D4;
}

/* Clipboard Panel */
.clipboard-title {
    color: #FFFFFF;
    font-weight: bold;
    font-size: 14px;
}

.clipboard-empty {
    color: #888888;
    font-style: italic;
    padding: 12px;
}

.clipboard-entry-text {
    color: #FFFFFF;
    font-size: 12px;
}

.clipboard-entry-age {
    color: #888888;
    font-size: 10px;
}

.clipboard-paste-btn {
    background-color: #0078D4;
    color: #FFFFFF;
    border-radius: 4px;
    border: none;
    padding: 4px 12px;
    font-size: 12px;
}

.clipboard-paste-btn:hover {
    background-color: #1A8AE8;
}

.clipboard-pin-btn {
    background-color: #3D3D3D;
    color: #FFFFFF;
    border-radius: 4px;
    border: none;
    padding: 4px 8px;
    font-size: 11px;
}

.clipboard-pin-btn:hover {
    background-color: #505050;
}

.clipboard-del-btn {
    background-color: transparent;
    color: #888888;
    border: none;
    padding: 2px 6px;
    font-size: 16px;
}

.clipboard-del-btn:hover {
    color: #FF4444;
}

.clipboard-clear-btn {
    background-color: transparent;
    color: #888888;
    border: 1px solid #505050;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 11px;
}

.clipboard-clear-btn:hover {
    color: #FFFFFF;
    border-color: #888888;
}

/* Emoji Picker */
.emoji-cat-btn {
    background-color: transparent;
    border: none;
    padding: 4px 8px;
    font-size: 18px;
    border-radius: 4px;
}

.emoji-cat-btn:hover {
    background-color: #3D3D3D;
}

.emoji-cat-active {
    background-color: #0078D4 !important;
    border-radius: 4px;
}

.emoji-btn {
    background-color: transparent;
    border: none;
    padding: 2px;
    font-size: 22px;
    min-width: 34px;
    min-height: 34px;
    border-radius: 4px;
}

.emoji-btn:hover {
    background-color: #3D3D3D;
}

.emoji-btn:active {
    background-color: #0078D4;
}

.emoji-category-label {
    color: #888888;
    font-size: 11px;
    padding: 2px 4px;
}

/* Language Switcher */
.lang-toggle-btn {
    background-color: #3D3D3D;
    color: #FFFFFF;
    border-radius: 4px;
    border: 1px solid #505050;
    padding: 4px 12px;
    font-weight: bold;
    font-size: 12px;
    min-width: 40px;
}

.lang-toggle-btn:hover {
    background-color: #505050;
    border-color: #0078D4;
}

.lang-toggle-btn:active {
    background-color: #0078D4;
}
"""


def apply_win11_css():
    """Apply Win11 CSS styling to the default GTK screen."""
    try:
        css_provider = Gtk.CssProvider()
        css_provider.load_from_data(WIN11_PANEL_CSS.encode('utf-8'))
        screen = Gdk.Screen.get_default()
        if screen:
            Gtk.StyleContext.add_provider_for_screen(
                screen,
                css_provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
            _logger.info("Win11 CSS styling applied")
    except Exception as e:
        _logger.warning("Failed to apply Win11 CSS: {}".format(e))
