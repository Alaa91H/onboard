# -*- coding: utf-8 -*-

"""
Keyboard Widget Compact Mode Integration
Patches to integrate compact mode into the existing KeyboardWidget.

This module provides functions to patch the KeyboardWidget class
to support compact mode functionality.

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
from Onboard.CompactMode import (CompactModeManager, CompactModeButton,
                                 CompactModeGestureHandler,
                                 get_compact_manager)


def patch_keyboard_widget(KeyboardWidget):
    """
    Patch the KeyboardWidget class to add compact mode support.
    Call this function after importing KeyboardWidget.
    """
    
    # Store original methods
    original_init = KeyboardWidget.__init__
    original_on_draw = KeyboardWidget._on_draw
    original_cleanup = KeyboardWidget.cleanup
    
    def patched_init(self, keyboard):
        """Patched __init__ to add compact mode support."""
        # Call original __init__
        original_init(self, keyboard)
        
        # Initialize compact mode
        self._compact_manager = CompactModeManager(self)
        self._compact_button = CompactModeButton(self, self._compact_manager)
        self._compact_gesture = CompactModeGestureHandler(self._compact_manager)
        
        # Add keyboard shortcut for compact mode (Ctrl+Shift+C)
        self._setup_compact_shortcuts()
        
    def patched_on_draw(self, widget, cr):
        """Patched draw handler to draw compact mode button."""
        # Call original draw
        result = original_on_draw(self, widget, cr)
        
        # Draw compact mode button if enabled
        if self._compact_button.is_visible():
            self._draw_compact_button(cr)
        
        return result
    
    def patched_cleanup(self):
        """Patched cleanup to handle compact mode cleanup."""
        # Cleanup compact mode
        if hasattr(self, '_compact_manager'):
            self._compact_manager.set_enabled(False)
        
        # Call original cleanup
        original_cleanup(self)
    
    def _setup_compact_shortcuts(self):
        """Setup keyboard shortcuts for compact mode."""
        # This will be connected when the widget is added to a window
        pass
    
    def _draw_compact_button(self, cr):
        """Draw the compact mode toggle button."""
        # Get the button rectangle
        rect = self._compact_button.get_rect()
        if rect.is_empty():
            return
        
        # Draw button background
        cr.set_source_rgba(0.3, 0.3, 0.3, 0.8)
        cr.rectangle(rect.x, rect.y, rect.w, rect.h)
        cr.fill()
        
        # Draw button label
        if self._compact_manager.is_enabled():
            label = "▼"  # Down arrow when in compact mode
        else:
            label = "▲"  # Up arrow when in full mode
        
        # Set font
        cr.select_font_face("sans", 0, 0)
        cr.set_font_size(12)
        cr.set_source_rgba(1.0, 1.0, 1.0, 1.0)
        
        # Center the label
        extents = cr.text_extents(label)
        x = rect.x + (rect.w - extents.width) / 2
        y = rect.y + (rect.h + extents.height) / 2
        
        cr.move_to(x, y)
        cr.show_text(label)
    
    def toggle_compact_mode(self):
        """Toggle compact mode on/off."""
        self._compact_manager.toggle()
    
    def cycle_compact_mode(self):
        """Cycle through keyboard modes."""
        self._compact_manager.cycle_mode()
    
    def is_compact_mode(self):
        """Check if in compact mode."""
        return self._compact_manager.is_enabled()
    
    def get_compact_manager(self):
        """Get the compact mode manager."""
        return self._compact_manager
    
    def update_compact_button_rect(self):
        """Update the compact mode button rectangle."""
        # Position the button in the top-right corner
        alloc = self.get_allocation()
        button_size = 24
        margin = 4
        
        rect = Rect(
            alloc.width - button_size - margin,
            margin,
            button_size,
            button_size
        )
        self._compact_button.set_rect(rect)
    
    def on_compact_button_click(self, x, y):
        """Handle click on the compact mode button."""
        if self._compact_button.hit_test((x, y)):
            self._compact_button.on_click()
            return True
        return False
    
    # Apply patches
    KeyboardWidget.__init__ = patched_init
    KeyboardWidget._on_draw = patched_on_draw
    KeyboardWidget.cleanup = patched_cleanup
    KeyboardWidget.toggle_compact_mode = toggle_compact_mode
    KeyboardWidget.cycle_compact_mode = cycle_compact_mode
    KeyboardWidget.is_compact_mode = is_compact_mode
    KeyboardWidget.get_compact_manager = get_compact_manager
    KeyboardWidget.update_compact_button_rect = update_compact_button_rect
    KeyboardWidget.on_compact_button_click = on_compact_button_click
    
    return KeyboardWidget


# Auto-patch when imported
def auto_patch():
    """Automatically patch KeyboardWidget when this module is imported."""
    try:
        from Onboard.KeyboardWidget import KeyboardWidget
        patch_keyboard_widget(KeyboardWidget)
        return True
    except ImportError:
        return False
