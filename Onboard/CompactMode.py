# -*- coding: utf-8 -*-

"""
Compact Mode for Onboard
Provides support for a minimized floating keyboard mode inspired by
the Windows 11 touch keyboard compact view.

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

import math
from Onboard.Version import require_gi_versions
require_gi_versions()
from gi.repository import GLib, Gdk, Gtk

from Onboard.utils import Rect
from Onboard.Timer import Timer

### Logging ###
import logging
_logger = logging.getLogger("CompactMode")
###############

### Config Singleton ###
from Onboard.Config import Config
config = Config()
########################


class CompactModeManager:
    """
    Manages the compact/minimized floating keyboard mode.
    
    When enabled, the keyboard shrinks to a minimal size showing only
    the most essential keys, similar to the Windows 11 touch keyboard
    compact view.
    """
    
    # Compact mode states
    STATE_FULL = 0       # Full keyboard
    STATE_COMPACT = 1    # Compact/minimized mode
    STATE_MINI = 2       # Minimal floating input
    
    # Default compact dimensions (percentage of full keyboard)
    COMPACT_WIDTH_RATIO = 0.45   # 45% of full width
    COMPACT_HEIGHT_RATIO = 0.60  # 60% of full height
    MINI_WIDTH_RATIO = 0.25      # 25% of full width
    MINI_HEIGHT_RATIO = 0.35     # 35% of full height
    
    def __init__(self, keyboard_widget):
        self._keyboard_widget = keyboard_widget
        self._state = self.STATE_FULL
        self._enabled = False
        self._compact_rect = Rect()
        self._full_rect = Rect()
        self._restore_rect = Rect()
        self._animation_timer = Timer()
        self._animation_progress = 0.0
        self._animation_duration = 0.3  # seconds
        
        # Connect to config changes
        self._connect_config_signals()
        
    def _connect_config_signals(self):
        """Connect to configuration signals for compact mode."""
        try:
            # Listen for keyboard show/hide events
            config.keyboard.connect("notify::visible", 
                                   self._on_visibility_changed)
        except Exception as e:
            _logger.debug("Could not connect to config signals: {}".format(e))
    
    def _on_visibility_changed(self, *args):
        """Handle keyboard visibility changes."""
        if self._enabled:
            self._update_compact_position()
    
    def is_enabled(self):
        """Check if compact mode is enabled."""
        return self._enabled
    
    def get_state(self):
        """Get current compact mode state."""
        return self._state
    
    def set_enabled(self, enabled):
        """Enable or disable compact mode."""
        if self._enabled == enabled:
            return
            
        self._enabled = enabled
        
        if enabled:
            self._save_full_rect()
            self._state = self.STATE_COMPACT
            self._transition_to_compact()
        else:
            self._state = self.STATE_FULL
            self._transition_to_full()
        
        _logger.debug("Compact mode {}".format("enabled" if enabled else "disabled"))
    
    def toggle(self):
        """Toggle compact mode on/off."""
        self.set_enabled(not self._enabled)
    
    def cycle_mode(self):
        """Cycle through keyboard modes: Full -> Compact -> Mini -> Full"""
        if self._state == self.STATE_FULL:
            self._save_full_rect()
            self._state = self.STATE_COMPACT
            self._transition_to_compact()
        elif self._state == self.STATE_COMPACT:
            self._state = self.STATE_MINI
            self._transition_to_mini()
        else:
            self._state = self.STATE_FULL
            self._transition_to_full()
        
        _logger.debug("Cycled to mode: {}".format(
            ["Full", "Compact", "Mini"][self._state]))
    
    def _save_full_rect(self):
        """Save the current full keyboard rectangle for restoration."""
        kbd_window = self._keyboard_widget.get_kbd_window()
        if kbd_window:
            alloc = kbd_window.get_allocation()
            self._full_rect = Rect(alloc.x, alloc.y, alloc.width, alloc.height)
            self._restore_rect = Rect(alloc.x, alloc.y, alloc.width, alloc.height)
    
    def _transition_to_compact(self):
        """Transition keyboard to compact mode."""
        self._calculate_compact_rect()
        self._apply_compact_dimensions()
    
    def _transition_to_mini(self):
        """Transition keyboard to mini mode."""
        self._calculate_mini_rect()
        self._apply_compact_dimensions()
    
    def _transition_to_full(self):
        """Transition keyboard back to full mode."""
        if not self._restore_rect.is_empty():
            self._apply_rect(self._restore_rect)
    
    def _calculate_compact_rect(self):
        """Calculate the rectangle for compact mode."""
        if self._full_rect.is_empty():
            return
            
        width = int(self._full_rect.w * self.COMPACT_WIDTH_RATIO)
        height = int(self._full_rect.h * self.COMPACT_HEIGHT_RATIO)
        
        # Center on the full keyboard position
        x = self._full_rect.x + (self._full_rect.w - width) // 2
        y = self._full_rect.y + (self._full_rect.h - height) // 2
        
        self._compact_rect = Rect(x, y, width, height)
    
    def _calculate_mini_rect(self):
        """Calculate the rectangle for mini mode."""
        if self._full_rect.is_empty():
            return
            
        width = int(self._full_rect.w * self.MINI_WIDTH_RATIO)
        height = int(self._full_rect.h * self.MINI_HEIGHT_RATIO)
        
        # Position at the top of the full keyboard
        x = self._full_rect.x + (self._full_rect.w - width) // 2
        y = self._full_rect.y
        
        self._compact_rect = Rect(x, y, width, height)
    
    def _apply_compact_dimensions(self):
        """Apply the calculated compact dimensions to the keyboard window."""
        if self._compact_rect.is_empty():
            return
            
        kbd_window = self._keyboard_widget.get_kbd_window()
        if kbd_window:
            # Resize the window
            kbd_window.resize(
                int(self._compact_rect.w),
                int(self._compact_rect.h)
            )
            
            # Reposition the window
            kbd_window.move(
                int(self._compact_rect.x),
                int(self._compact_rect.y)
            )
            
            # Invalidate the keyboard layout to redraw
            self._keyboard_widget.invalidate_ui()
            self._keyboard_widget.commit_ui_updates()
    
    def _apply_rect(self, rect):
        """Apply a rectangle to the keyboard window."""
        kbd_window = self._keyboard_widget.get_kbd_window()
        if kbd_window:
            kbd_window.move(int(rect.x), int(rect.y))
            kbd_window.resize(int(rect.w), int(rect.h))
            
            self._keyboard_widget.invalidate_ui()
            self._keyboard_widget.commit_ui_updates()
    
    def _update_compact_position(self):
        """Update compact mode position when keyboard moves."""
        if self._state == self.STATE_FULL:
            return
            
        kbd_window = self._keyboard_widget.get_kbd_window()
        if kbd_window:
            alloc = kbd_window.get_allocation()
            self._full_rect = Rect(alloc.x, alloc.y, alloc.width, alloc.height)
            
            if self._state == self.STATE_COMPACT:
                self._calculate_compact_rect()
            elif self._state == self.STATE_MINI:
                self._calculate_mini_rect()
    
    def get_compact_scale(self):
        """
        Get the scale factor for compact mode.
        Used to scale UI elements appropriately.
        """
        if self._state == self.STATE_FULL:
            return 1.0
        elif self._state == self.STATE_COMPACT:
            return self.COMPACT_WIDTH_RATIO
        else:
            return self.MINI_WIDTH_RATIO
    
    def get_key_size_override(self):
        """
        Get the key size override for compact mode.
        Returns None if no override is needed.
        """
        if self._state == self.STATE_FULL:
            return None
            
        scale = self.get_compact_scale()
        # In compact mode, we want proportionally smaller keys
        return max(0.5, scale * 1.2)  # Minimum 50% key size


class CompactModeButton:
    """
    A button that toggles compact mode.
    Can be placed in the keyboard layout.
    """
    
    def __init__(self, keyboard_widget, compact_manager):
        self._keyboard_widget = keyboard_widget
        self._compact_manager = compact_manager
        self._visible = True
        self._rect = Rect()
        
    def set_visible(self, visible):
        """Show or hide the compact mode button."""
        self._visible = visible
    
    def is_visible(self):
        """Check if the button is visible."""
        return self._visible
    
    def set_rect(self, rect):
        """Set the button rectangle."""
        self._rect = rect
    
    def get_rect(self):
        """Get the button rectangle."""
        return self._rect
    
    def hit_test(self, point):
        """Test if a point is within the button."""
        return self._rect.is_point_within(point)
    
    def on_click(self):
        """Handle button click."""
        self._compact_manager.toggle()
        self._keyboard_widget.invalidate_ui()
        self._keyboard_widget.commit_ui_updates()


class CompactModeGestureHandler:
    """
    Handles gestures for compact mode switching.
    Supports swipe gestures to switch between modes.
    """
    
    # Swipe thresholds
    SWIPE_THRESHOLD = 50  # pixels
    SWIPE_TIMEOUT = 0.5   # seconds
    
    def __init__(self, compact_manager):
        self._compact_manager = compact_manager
        self._start_point = None
        self._start_time = 0.0
        
    def on_touch_begin(self, point):
        """Handle touch begin event."""
        self._start_point = point
        self._start_time = GLib.get_monotonic_time() / 1000000.0
    
    def on_touch_end(self, point):
        """Handle touch end event."""
        if self._start_point is None:
            return False
            
        # Calculate swipe distance and direction
        dx = point[0] - self._start_point[0]
        dy = point[1] - self._start_point[1]
        distance = math.sqrt(dx * dx + dy * dy)
        
        # Check if it's a valid swipe
        elapsed = GLib.get_monotonic_time() / 1000000.0 - self._start_time
        if distance > self.SWIPE_THRESHOLD and elapsed < self.SWIPE_TIMEOUT:
            # Determine swipe direction
            if abs(dx) > abs(dy):
                # Horizontal swipe
                if dx > 0:
                    # Swipe right - switch to compact mode
                    self._compact_manager.set_enabled(True)
                else:
                    # Swipe left - switch to full mode
                    self._compact_manager.set_enabled(False)
            else:
                # Vertical swipe
                if dy > 0:
                    # Swipe down - cycle to next mode
                    self._compact_manager.cycle_mode()
                else:
                    # Swipe up - cycle to previous mode
                    self._compact_manager.cycle_mode()
            
            self._start_point = None
            return True
            
        self._start_point = None
        return False


# Module-level instance for easy access
_compact_manager = None

def get_compact_manager(keyboard_widget=None):
    """Get or create the compact mode manager instance."""
    global _compact_manager
    if _compact_manager is None and keyboard_widget is not None:
        _compact_manager = CompactModeManager(keyboard_widget)
    return _compact_manager

def is_compact_mode_enabled():
    """Check if compact mode is currently enabled."""
    global _compact_manager
    if _compact_manager is not None:
        return _compact_manager.is_enabled()
    return False

def toggle_compact_mode():
    """Toggle compact mode on/off."""
    global _compact_manager
    if _compact_manager is not None:
        _compact_manager.toggle()

def cycle_compact_mode():
    """Cycle through keyboard modes."""
    global _compact_manager
    if _compact_manager is not None:
        _compact_manager.cycle_mode()
