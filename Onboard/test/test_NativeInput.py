# -*- coding: utf-8 -*-

import unittest
from unittest.mock import patch

from Onboard import NativeInput


KEYMAP = b'xkb_keymap { xkb_keycodes "(unnamed)" {}; }\n'


class TestNativeInput(unittest.TestCase):

    def _exercise_contract(self, engine, expected_transport):
        self.assertEqual(expected_transport, engine.transport)
        self.assertFalse(engine.is_open)
        engine.open("validation-only")
        self.assertTrue(engine.is_open)
        with self.assertRaises(NativeInput.NativeInputError) as error:
            engine.key(38, True, 0)
        self.assertEqual("keymap-not-installed", error.exception.code)
        engine.install_keymap(KEYMAP)
        engine.key(38, True, 1)
        engine.key(39, True, 2)
        self.assertEqual([38, 39], engine.pressed_keycodes)
        engine.key(38, False, 3)
        self.assertEqual([39], engine.pressed_keycodes)
        engine.modifiers(1, 2, 4, 3)
        self.assertEqual((1, 2, 4, 3), engine.modifier_state)
        with self.assertRaises(NativeInput.NativeInputError) as error:
            engine.key(768, True, 4)
        self.assertEqual("invalid-keycode", error.exception.code)
        engine.close()
        self.assertFalse(engine.is_open)
        self.assertEqual([], engine.pressed_keycodes)

    def test_fallback_contract(self):
        self._exercise_contract(NativeInput.create_input_engine("fallback"),
                                "python-fallback")

    def test_invalid_keymaps_are_rejected(self):
        engine = NativeInput.create_input_engine("fallback")
        for keymap in (b"", b"xkb\x00", b"\xff"):
            with self.subTest(keymap=keymap):
                with self.assertRaises(NativeInput.NativeInputError) as error:
                    engine.install_keymap(keymap)
                self.assertEqual("invalid-keymap", error.exception.code)

    def test_auto_mode_has_a_safe_fallback_without_extension(self):
        with patch.object(NativeInput, "_load_native_module",
                          return_value=(None, "not installed")):
            status = NativeInput.get_status("auto")
            self.assertEqual("python-fallback", status.selected)
            self.assertFalse(status.available)
            self.assertEqual("not installed", status.detail)
            self.assertIsInstance(NativeInput.create_input_engine("auto"),
                                  NativeInput.FallbackInputEngine)

    def test_native_mode_reports_a_missing_extension_explicitly(self):
        with patch.object(NativeInput, "_load_native_module",
                          return_value=(None, "not installed")):
            status = NativeInput.get_status("native")
            self.assertEqual("unavailable", status.selected)
            with self.assertRaises(NativeInput.NativeInputUnavailable):
                NativeInput.create_input_engine("native")

    def test_rust_contract_when_extension_was_built(self):
        status = NativeInput.get_status("native")
        if not status.available:
            self.skipTest("Rust extension is not part of this fallback-only build")
        self._exercise_contract(NativeInput.create_input_engine("native"),
                                "rust-validation")

    def test_invalid_modes_are_rejected(self):
        with self.assertRaises(NativeInput.NativeInputError):
            NativeInput.get_status("unsupported")
