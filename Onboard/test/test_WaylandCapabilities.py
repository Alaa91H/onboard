#!/usr/bin/python3

import os
import unittest
from unittest.mock import patch

from Onboard import WaylandUtils


class TestWaylandCapabilities(unittest.TestCase):

    def test_desktop_environment_parses_common_xdg_identifiers(self):
        cases = {
            "KDE:PLASMA": "kde",
            "GNOME": "gnome",
            "sway": "wlr-compatible",
            "Hyprland": "wlr-compatible",
            "XFCE": "x11-desktop",
        }
        for desktop, expected in cases.items():
            with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": desktop},
                            clear=True):
                self.assertEqual(expected,
                                 WaylandUtils.get_desktop_environment())

    @patch.object(WaylandUtils, "is_wayland", return_value=False)
    def test_x11_capabilities_are_movable_and_switchable(self, _is_wayland):
        caps = WaylandUtils.get_runtime_capabilities()
        self.assertEqual("x11", caps.window_strategy)
        self.assertEqual("x11", caps.input_source_strategy)
        self.assertTrue(caps.movable)

    @patch.object(WaylandUtils, "is_wayland", return_value=True)
    def test_kde_wayland_uses_kwin_and_dbus(self, _is_wayland):
        with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "KDE"}, clear=True):
            caps = WaylandUtils.get_runtime_capabilities()
        self.assertEqual("kwin-rule", caps.window_strategy)
        self.assertEqual("kde-dbus", caps.input_source_strategy)
        self.assertTrue(caps.movable)

    @patch.object(WaylandUtils, "is_wayland", return_value=True)
    @patch.object(WaylandUtils, "is_layer_shell_available", return_value=True)
    def test_wlr_wayland_reports_placement_without_false_input_claims(
            self, _layer_shell, _is_wayland):
        with patch.dict(os.environ, {"XDG_CURRENT_DESKTOP": "sway"}, clear=True):
            caps = WaylandUtils.get_runtime_capabilities()
        self.assertEqual("layer-shell", caps.window_strategy)
        self.assertEqual("unavailable", caps.input_source_strategy)
        self.assertFalse(caps.movable)
        self.assertIn("XWayland", caps.warning)
