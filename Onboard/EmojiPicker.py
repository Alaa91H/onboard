# -*- coding: utf-8 -*-

"""
Emoji Picker for Onboard
Provides a searchable emoji panel for the floating keyboard.
Inspired by the Windows 11 Touch Keyboard emoji picker.

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
import json

from Onboard.Version import require_gi_versions
require_gi_versions()
from gi.repository import GLib, Gdk, Gtk, Pango

### Logging ###
import logging
_logger = logging.getLogger("EmojiPicker")
###############

### Config Singleton ###
from Onboard.Config import Config
config = Config()
########################


# Emoji categories with their display names and sample emojis
EMOJI_CATEGORIES = {
    "smileys": {
        "name": "Smileys & People",
        "icon": "😀",
        "emojis": [
            "😀", "😃", "😄", "😁", "😆", "😅", "🤣", "😂", "🙂", "🙃",
            "😉", "😊", "😇", "🥰", "😍", "🤩", "😘", "😗", "😚", "😙",
            "🥲", "😋", "😛", "😜", "🤪", "😝", "🤑", "🤗", "🤭", "🤫",
            "🤔", "🫡", "🤐", "🤨", "😐", "😑", "😶", "😏", "😒", "🙄",
            "😬", "🤥", "😌", "😔", "😪", "🤤", "😴", "😷", "🤒", "🤕",
            "🤢", "🤮", "🥵", "🥶", "🥴", "😵", "🤯", "🤠", "🥳", "🥸",
            "😎", "🤓", "🧐", "😕", "😟", "🙁", "😮", "😯", "😲", "😳",
            "🥺", "😦", "😧", "😨", "😰", "😥", "😢", "😭", "😱", "😖",
            "😣", "😞", "😓", "😩", "😫", "🥱", "😤", "😡", "😠", "🤬",
            "😈", "👿", "💀", "☠️", "💩", "🤡", "👹", "👺", "👻", "👽",
            "👾", "🤖", "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍",
            "🤎", "💔", "❤️‍🔥", "❤️‍🩹", "❣️", "💕", "💞", "💓", "💗", "💖",
            "💘", "💝", "💟", "👋", "🤚", "🖐️", "✋", "🖖", "👌", "🤌",
            "🤏", "✌️", "🤞", "🫰", "🤟", "🤘", "🤙", "👈", "👉", "👆",
            "🖕", "👇", "☝️", "🫵", "👍", "👎", "✊", "👊", "🤛", "🤜",
            "👏", "🙌", "🫶", "👐", "🤲", "🤝", "🙏", "💪", "🦾", "🦿",
        ],
    },
    "nature": {
        "name": "Animals & Nature",
        "icon": "🐶",
        "emojis": [
            "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐻‍❄️", "🐨",
            "🐯", "🦁", "🐮", "🐷", "🐸", "🐵", "🙈", "🙉", "🙊", "🐒",
            "🐔", "🐧", "🐦", "🐤", "🐣", "🐥", "🦆", "🦅", "🦉", "🦇",
            "🐺", "🐗", "🐴", "🦄", "🐝", "🪱", "🐛", "🦋", "🐌", "🐞",
            "🐜", "🪰", "🪲", "🪳", "🦟", "🦗", "🕷️", "🦂", "🐢", "🐍",
            "🦎", "🦖", "🦕", "🐙", "🦑", "🦐", "🦞", "🦀", "🐡", "🐠",
            "🐟", "🐬", "🐳", "🐋", "🦈", "🦭", "🐊", "🐅", "🐆", "🦓",
            "🦍", "🦧", "🐘", "🦛", "🦏", "🐪", "🐫", "🦒", "🦘", "🦬",
            "🐃", "🐂", "🐄", "🐎", "🐖", "🐏", "🐑", "🦙", "🐐", "🦌",
            "🌸", "💮", "🏵️", "🌹", "🥀", "🌺", "🌻", "🌼", "🌷", "🌱",
            "🪴", "🌲", "🌳", "🌴", "🌵", "🌾", "🌿", "☘️", "🍀", "🍁",
            "🍂", "🍃", "🍄", "🌰", "🌍", "🌎", "🌏", "🌕", "🌙", "⭐",
        ],
    },
    "food": {
        "name": "Food & Drink",
        "icon": "🍕",
        "emojis": [
            "🍇", "🍈", "🍉", "🍊", "🍋", "🍌", "🍍", "🥭", "🍎", "🍏",
            "🍐", "🍑", "🍒", "🍓", "🫐", "🥝", "🍅", "🫒", "🥥", "🥑",
            "🍆", "🥔", "🥕", "🌽", "🌶️", "🫑", "🥒", "🥬", "🥦", "🧄",
            "🧅", "🍄", "🥜", "🫘", "🌰", "🍞", "🥐", "🥖", "🫓", "🥨",
            "🥯", "🥞", "🧇", "🧀", "🍖", "🍗", "🥩", "🥓", "🍔", "🍟",
            "🍕", "🌭", "🥪", "🌮", "🌯", "🫔", "🥙", "🧆", "🥚", "🍳",
            "🥘", "🍲", "🫕", "🥣", "🥗", "🍿", "🧈", "🧂", "🥫", "🍱",
            "🍘", "🍙", "🍚", "🍛", "🍜", "🦪", "🍣", "🍤", "🍥", "🥮",
            "🍡", "🥟", "🥠", "🥡", "🦀", "🦞", "🦐", "🦑", "🦪", "🍦",
            "🍧", "🍨", "🍩", "🍪", "🎂", "🍰", "🧁", "🥧", "🍫", "🍬",
            "🍭", "🍮", "🍯", "🍼", "🥛", "☕", "🫖", "🍵", "🍶", "🍾",
            "🍷", "🍸", "🍹", "🍺", "🍻", "🥂", "🥃", "🫗", "🥤", "🧋",
        ],
    },
    "activities": {
        "name": "Activities",
        "icon": "⚽",
        "emojis": [
            "⚽", "🏀", "🏈", "⚾", "🥎", "🎾", "🏐", "🏉", "🥏", "🎱",
            "🪀", "🏓", "🏸", "🏒", "🏑", "🥍", "🏏", "🪃", "🥅", "⛳",
            "🪁", "🏹", "🎣", "🤿", "🥊", "🥋", "🎽", "🛹", "🛼", "🛷",
            "⛸️", "🥌", "🎿", "🎯", "🪀", "🪁", "🎮", "🕹️", "🎲", "🧩",
            "🎭", "🎨", "🧵", "🪡", "🧶", "🪢", "🎬", "🎤", "🎧", "🎼",
            "🎹", "🥁", "🪘", "🎷", "🎺", "🪗", "🎸", "🪕", "🎻", "🎰",
        ],
    },
    "travel": {
        "name": "Travel & Places",
        "icon": "🚗",
        "emojis": [
            "🚗", "🚕", "🚙", "🚌", "🚎", "🏎️", "🚓", "🚑", "🚒", "🚐",
            "🛻", "🚚", "🚛", "🚜", "🏍️", "🛵", "🦽", "🦼", "🛺", "🚲",
            "🛴", "🛹", "🛼", "🚏", "🛣️", "🛤️", "🛞", "⛽", "🛞", "🚨",
            "🚥", "🚦", "🛑", "🚧", "⚓", "⛵", "🛶", "🚤", "🛳️", "⛴️",
            "🛥️", "🚢", "✈️", "🛩️", "🛫", "🛬", "🪂", "💺", "🚁", "🚟",
            "🚠", "🚡", "🛰️", "🚀", "🛸", "🌍", "🌎", "🌏", "🗺️", "🧭",
            "🏠", "🏡", "🏢", "🏣", "🏤", "🏥", "🏦", "🏨", "🏩", "🏪",
            "🏫", "🏬", "🏭", "🏯", "🏰", "💒", "🗼", "🗽", "⛪", "🕌",
        ],
    },
    "objects": {
        "name": "Objects",
        "icon": "💡",
        "emojis": [
            "⌚", "📱", "📲", "💻", "⌨️", "🖥️", "🖨️", "🖱️", "🖲️", "🕹️",
            "🗜️", "💽", "💾", "💿", "📀", "📼", "📷", "📸", "📹", "🎥",
            "📽️", "🎞️", "📞", "☎️", "📟", "📠", "📺", "📻", "🎙️", "🎚️",
            "🎛️", "🧭", "⏱️", "⏲️", "⏰", "🕰️", "⌛", "⏳", "📡", "🔋",
            "🔌", "💡", "🔦", "🕯️", "🧯", "🛢️", "💸", "💵", "💴", "💶",
            "💷", "🪙", "💰", "💳", "🪪", "⚖️", "🧰", "🪛", "🔧", "🔩",
            "⚙️", "🗜️", "⛏️", "🛠️", "⚒️", "🔨", "🪚", "🔗", "⛓️", "🧲",
        ],
    },
    "symbols": {
        "name": "Symbols",
        "icon": "❤️",
        "emojis": [
            "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "🤎", "💔",
            "❣️", "💕", "💞", "💓", "💗", "💖", "💘", "💝", "✝️", "☪️",
            "🕉️", "☸️", "✡️", "🔯", "🕎", "☯️", "☦️", "🛐", "⛎", "♈",
            "♉", "♊", "♋", "♌", "♍", "♎", "♏", "♐", "♑", "♒",
            "♓", "🆔", "⚛️", "🉑", "☢️", "☣️", "📴", "📳", "🈶", "🈚",
            "🈸", "🈺", "🈷️", "✴️", "🆚", "💮", "🉐", "㊙️", "㊗️", "🈴",
            "🈹", "🈲", "🅰️", "🅱️", "🆎", "🆑", "🅾️", "🆘", "❌", "⭕",
            "⛔", "📛", "🚫", "💯", "💢", "♨️", "🚷", "🚯", "🚳", "🚱",
        ],
    },
    "flags": {
        "name": "Flags",
        "icon": "🏁",
        "emojis": [
            "🏁", "🚩", "🎌", "🏴", "🏳️", "🏳️‍🌈", "🏳️‍⚧️", "🏴‍☠️", "🇦🇫", "🇦🇱",
            "🇩🇿", "🇦🇸", "🇦🇩", "🇦🇴", "🇦🇮", "🇦🇶", "🇦🇬", "🇦🇷", "🇦🇲", "🇦🇼",
            "🇦🇺", "🇦🇹", "🇦🇿", "🇧🇸", "🇧🇭", "🇧🇩", "🇧🇧", "🇧🇾", "🇧🇪", "🇧🇿",
            "🇧🇯", "🇧🇲", "🇧🇹", "🇧🇴", "🇧🇦", "🇧🇼", "🇧🇷", "🇧🇳", "🇧🇬", "🇧🇫",
            "🇧🇮", "🇨🇻", "🇰🇭", "🇨🇲", "🇨🇦", "🇰🇾", "🇨🇫", "🇹🇩", "🇨🇱", "🇨🇳",
            "🇨🇴", "🇰🇲", "🇨🇬", "🇨🇩", "🇨🇰", "🇨🇷", "🇨🇮", "🇭🇷", "🇨🇺", "🇨🇼",
            "🇨🇾", "🇨🇿", "🇩🇰", "🇩🇯", "🇩🇲", "🇩🇴", "🇪🇨", "🇪🇬", "🇸🇻", "🇬🇶",
            "🇪🇷", "🇪🇪", "🇪🇹", "🇫🇯", "🇫🇮", "🇫🇷", "🇬🇫", "🇵🇫", "🇹🇫", "🇬🇦",
        ],
    },
}


class EmojiSearchEngine:
    """Simple emoji search by category and character matching."""

    def __init__(self):
        self._all_emojis = []
        for cat_id, cat_data in EMOJI_CATEGORIES.items():
            for emoji in cat_data["emojis"]:
                self._all_emojis.append((emoji, cat_id))

    def search(self, query):
        """Search emojis by query string."""
        if not query:
            return self._all_emojis

        query = query.lower().strip()
        results = []

        # Search in category names
        for cat_id, cat_data in EMOJI_CATEGORIES.items():
            if query in cat_data["name"].lower():
                for emoji in cat_data["emojis"]:
                    results.append((emoji, cat_id))

        # Search in emoji aliases/keywords (if we add them later)
        # For now just match by category

        return results

    def get_emojis_by_category(self, category_id):
        """Get all emojis in a category."""
        cat = EMOJI_CATEGORIES.get(category_id, {})
        return [(e, category_id) for e in cat.get("emojis", [])]

    def get_categories(self):
        """Get all category IDs and names."""
        return [(cat_id, cat_data["name"], cat_data["icon"])
                for cat_id, cat_data in EMOJI_CATEGORIES.items()]


class EmojiPicker(Gtk.Box):
    """
    GTK widget displaying a searchable emoji picker panel.
    Layout: category tabs at top, search bar, grid of emojis.
    """

    EMOJI_BUTTON_SIZE = 36
    GRID_COLUMNS = 8
    MAX_RECENT = 18

    def __init__(self, on_emoji_selected=None):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self._on_emoji_selected = on_emoji_selected
        self._search_engine = EmojiSearchEngine()
        self._recent_emojis = []
        self._current_category = "smileys"

        self.set_margin_start(4)
        self.set_margin_end(4)
        self.set_margin_top(4)
        self.set_margin_bottom(4)

        self._build_ui()

    def _build_ui(self):
        """Build the emoji picker UI."""

        # ---- Category tabs ----
        self._category_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self._category_buttons = {}

        for cat_id, cat_name, cat_icon in self._search_engine.get_categories():
            btn = Gtk.Button(label=cat_icon)
            btn.set_tooltip_text(cat_name)
            btn.get_style_context().add_class("emoji-cat-btn")
            btn.connect("clicked", self._on_category_clicked, cat_id)
            self._category_box.pack_start(btn, True, True, 1)
            self._category_buttons[cat_id] = btn

        self.pack_start(self._category_box, False, False, 2)

        # ---- Search bar ----
        search_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        self._search_entry = Gtk.SearchEntry()
        self._search_entry.set_placeholder_text("Search emoji...")
        self._search_entry.connect("search-changed", self._on_search_changed)
        search_box.pack_start(self._search_entry, True, True, 4)
        self.pack_start(search_box, False, False, 2)

        # ---- Emoji grid (in scrolled window) ----
        self._scroll = Gtk.ScrolledWindow()
        self._scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self._scroll.set_min_content_height(200)
        self._scroll.set_max_content_height(350)

        self._flow_box = Gtk.FlowBox()
        self._flow_box.set_homogeneous(True)
        self._flow_box.set_column_spacing(2)
        self._flow_box.set_row_spacing(2)
        self._flow_box.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self._flow_box.set_max_children_per_line(self.GRID_COLUMNS)
        self._flow_box.set_min_children_per_line(self.GRID_COLUMNS)
        self._flow_box.connect("child-activated", self._on_emoji_activated)

        self._scroll.add(self._flow_box)
        self.pack_start(self._scroll, True, True, 0)

        # ---- Category label at bottom ----
        self._category_label = Gtk.Label(label="")
        self._category_label.get_style_context().add_class("emoji-category-label")
        self.pack_start(self._category_label, False, False, 2)

        # Populate with default category
        self._show_category("smileys")

    def _on_category_clicked(self, button, cat_id):
        """Handle category tab click."""
        self._search_entry.set_text("")
        self._current_category = cat_id
        self._show_category(cat_id)

    def _on_search_changed(self, entry):
        """Handle search text change."""
        query = entry.get_text().strip()
        if query:
            results = self._search_engine.search(query)
            self._show_emojis(results)
            self._category_label.set_text("Search results")
        else:
            self._show_category(self._current_category)

    def _show_category(self, cat_id):
        """Show emojis for a category."""
        emojis = self._search_engine.get_emojis_by_category(cat_id)
        self._show_emojis(emojis)
        cat = EMOJI_CATEGORIES.get(cat_id, {})
        self._category_label.set_text(cat.get("name", ""))

        # Highlight active category button
        for bid, btn in self._category_buttons.items():
            if bid == cat_id:
                btn.get_style_context().add_class("emoji-cat-active")
            else:
                btn.get_style_context().remove_class("emoji-cat-active")

    def _show_emojis(self, emoji_list):
        """Display emojis in the flow box."""
        # Clear existing
        for child in self._flow_box.get_children():
            self._flow_box.remove(child)

        for emoji, cat_id in emoji_list:
            btn = Gtk.Button(label=emoji)
            btn.set_size_request(self.EMOJI_BUTTON_SIZE, self.EMOJI_BUTTON_SIZE)
            btn.get_style_context().add_class("emoji-btn")
            btn.set_relief(Gtk.ReliefStyle.NONE)
            self._flow_box.add(btn)

        self._flow_box.show_all()

    def _on_emoji_activated(self, flow_box, child):
        """Handle emoji selection."""
        button = child.get_child()
        if button:
            emoji = button.get_label()
            self._add_recent(emoji)
            if self._on_emoji_selected:
                self._on_emoji_selected(emoji)

    def _add_recent(self, emoji):
        """Add emoji to recent list."""
        if emoji in self._recent_emojis:
            self._recent_emojis.remove(emoji)
        self._recent_emojis.insert(0, emoji)
        if len(self._recent_emojis) > self.MAX_RECENT:
            self._recent_emojis = self._recent_emojis[:self.MAX_RECENT]

    def get_recent_emojis(self):
        """Get list of recently used emojis."""
        return list(self._recent_emojis)
