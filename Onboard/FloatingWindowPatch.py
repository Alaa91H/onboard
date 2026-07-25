# -*- coding: utf-8 -*-

"""
Floating Window Patch for Onboard
Adds always-on-top floating mode with close button support.
Patch for KbdWindow to support Win11 floating keyboard behavior.

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
from gi.repository import GLib, Gdk, Gtk, GdkX11

### Logging ###
import logging
_logger = logging.getLogger("FloatingWindowPatch")
###############

### Config Singleton ###
from Onboard.Config import Config
config = Config()
########################


class FloatingWindowPatch:
    """
    Patches KbdWindow to support always-on-top floating mode.

    When floating mode is active:
    - Window stays above all other windows (set_keep_above)
    - Window does not auto-hide
    - Close button (X) is available on the keyboard
    - Window can be dragged by the title bar area
    """

    def __init__(self, kbd_window):
        self._kbd_window = kbd_window
        self._floating_enabled = False
        self._original_auto_show = None
        self._original_sticky = None

    def enable_floating_mode(self):
        """
        Enable always-on-top floating mode.
        The keyboard will stay visible until explicitly closed.
        """
        if self._floating_enabled:
            return

        window = self._kbd_window

        # Store original settings
        self._original_auto_show = getattr(config.auto_show, 'enabled', True)
        self._original_sticky = getattr(window, '_sticky', False)

        # Set window to always be on top
        if hasattr(window, 'set_keep_above'):
            window.set_keep_above(True)
            _logger.info("Window set to keep_above=True")

        # Mark window as sticky (won't auto-hide)
        if hasattr(window, '_sticky'):
            window._sticky = True

        # Disable auto-show/auto-hide while in floating mode
        if hasattr(config, 'auto_show'):
            try:
                config.auto_show.enabled = False
            except Exception:
                pass

        # Set window type hint for floating
        if hasattr(window, 'set_type_hint'):
            window.set_type_hint(Gdk.WindowTypeHint.DIALOG)

        # Skip taskbar (like a utility window)
        if hasattr(window, 'set_skip_taskbar_hint'):
            window.set_skip_taskbar_hint(True)

        self._floating_enabled = True
        _logger.info("Floating mode enabled")

    def disable_floating_mode(self):
        """Disable floating mode and restore original settings."""
        if not self._floating_enabled:
            return

        window = self._kbd_window

        # Restore auto-show
        if self._original_auto_show is not None and hasattr(config, 'auto_show'):
            try:
                config.auto_show.enabled = self._original_auto_show
            except Exception:
                pass

        # Restore sticky state
        if self._original_sticky is not None and hasattr(window, '_sticky'):
            window._sticky = self._original_sticky

        self._floating_enabled = False
        _logger.info("Floating mode disabled")

    def is_floating(self):
        """Check if floating mode is active."""
        return self._floating_enabled

    def handle_close_button(self):
        """
        Handle the close button click.
        Just hides the keyboard, doesn't quit the application.
        """
        window = self._kbd_window
        if window:
            window.transition_visible_to(False)
            _logger.info("Floating keyboard closed via close button")

    def handle_move_start(self):
        """
        Start dragging the keyboard window.
        Called when the user clicks and drags the title bar area.
        """
        window = self._kbd_window
        if window and hasattr(window, 'begin_move_drag'):
            # Use GTK's built-in window drag
            window.begin_move_drag(
                1,  # button
                int(Gdk.Time.current_time),
                int(Gdk.Time.current_time)
            )

    def ensure_always_on_top(self):
        """
        Re-apply keep_above if the window manager lost the state.
        Should be called periodically or after window state changes.
        """
        if not self._floating_enabled:
            return

        window = self._kbd_window
        if window and hasattr(window, 'set_keep_above'):
            window.set_keep_above(True)

    def make_keyboard_always_on_top(self, window):
        """
        Static helper to make any Gtk.Window always on top.
        Useful for the KbdWindow and popup windows.
        """
        if hasattr(window, 'set_keep_above'):
            window.set_keep_above(True)

        # Also set the _NET_WM_STATE_ABOVE hint directly on X11
        if hasattr(window, 'get_window'):
            gdk_window = window.get_window()
            if gdk_window and hasattr(gdk_window, 'get_xid'):
                try:
                    xid = gdk_window.get_xid()
                    # X11: set _NET_WM_STATE_ABOVE
                    display = Gdk.Display.get_default()
                    if hasattr(display, 'get_default_screen'):
                        screen = display.get_default_screen()
                        atom = Gdk.Atom.intern(
                            "_NET_WM_STATE_ABOVE", False)
                        # Use Gtk's property change
                        window.set_keep_above(True)
                except Exception as e:
                    _logger.debug("X11 above hint failed: {}".format(e))


def patch_kbd_window(kbd_window):
    """
    Apply floating window patches to a KbdWindow instance.
    Call this after KbdWindow is created.
    """
    patch = FloatingWindowPatch(kbd_window)

    # Store original show/hide methods
    original_show = None
    original_hide = None

    if hasattr(kbd_window, 'transition_visible_to'):
        original_show = kbd_window.transition_visible_to

    # Apply floating mode if Win11 layout is active
    layout = getattr(config.keyboard, 'layout', '')
    if "Win11" in str(layout) and "Floating" in str(layout):
        patch.enable_floating_mode()
        _logger.info("Win11 floating layout detected, floating mode enabled")

    # Attach patch to window for later access
    kbd_window._floating_patch = patch

    return patch


def ensure_floating_above(kbd_window):
    """
    Ensure the floating keyboard window stays above all others.
    Call this on window state changes, focus changes, etc.
    """
    if hasattr(kbd_window, '_floating_patch'):
        kbd_window._floating_patch.ensure_always_on_top()
