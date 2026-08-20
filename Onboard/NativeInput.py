# -*- coding: utf-8 -*-
#
# Copyright © 2026 Onboard contributors
#
# This file is part of Onboard.
#
# Onboard is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3 of the License, or
# (at your option) any later version.

"""Optional native-input capability boundary.

The established virtkey/uinput path remains the production key injector.  This
module exposes a narrow, testable contract for a future Rust transport while
keeping GTK, D-Bus, source-selection policy and localization in Python.

``ONBOARD_NATIVE_INPUT`` selects the implementation:

* ``auto`` (default): use Rust when bundled, otherwise use the safe validator.
* ``native``: require Rust and fail explicitly if the extension is unavailable.
* ``fallback``: always use the Python validator, useful for diagnostics/tests.

Neither implementation emits input events in this first milestone.  They
validate keymaps and record state only, so introducing the optional module
cannot alter the established key-injection behaviour.
"""

from __future__ import division, print_function, unicode_literals

from dataclasses import dataclass
import importlib
import os


MAX_KEYCODE = 767
MAX_KEYMAP_BYTES = 1_048_576


class NativeInputError(RuntimeError):
    """A stable native-input failure represented by a code and detail."""

    def __init__(self, message):
        message = str(message)
        code, separator, detail = message.partition(":")
        self.code = code
        self.detail = detail if separator else ""
        super(NativeInputError, self).__init__(message)


class NativeInputUnavailable(NativeInputError):
    """Raised only when the caller explicitly requires the Rust extension."""


@dataclass(frozen=True)
class NativeInputStatus:
    requested: str
    selected: str
    available: bool
    capabilities: tuple
    detail: str = ""


def _requested_mode(mode=None):
    requested = (mode if mode is not None else
                 os.environ.get("ONBOARD_NATIVE_INPUT", "auto"))
    requested = str(requested).strip().lower()
    aliases = {
        "0": "fallback", "false": "fallback", "off": "fallback",
        "1": "native", "true": "native", "on": "native",
    }
    requested = aliases.get(requested, requested)
    if requested not in ("auto", "native", "fallback"):
        raise NativeInputError("invalid-native-input-mode:{}".format(requested))
    return requested


def _load_native_module():
    try:
        return importlib.import_module("Onboard.onboard_native"), ""
    except ImportError as error:
        return None, str(error)


def get_status(mode=None):
    """Return a serializable view of the selected optional implementation."""
    requested = _requested_mode(mode)
    module, detail = _load_native_module()
    available = module is not None
    if requested == "fallback":
        return NativeInputStatus(requested, "python-fallback", available,
                                 ("keymap-validation", "event-state"))
    if available:
        return NativeInputStatus(requested, "rust-validation", True,
                                 tuple(module.runtime_capabilities()))
    if requested == "native":
        return NativeInputStatus(requested, "unavailable", False, (), detail)
    return NativeInputStatus(requested, "python-fallback", False,
                             ("keymap-validation", "event-state"), detail)


class RustInputEngine(object):
    """Normalize the PyO3 object to the same contract as the Python fallback."""

    transport = "rust-validation"

    def __init__(self, module):
        self._engine = module.InputEngine()

    @property
    def is_open(self):
        return self._engine.is_open

    @property
    def pressed_keycodes(self):
        return self._engine.pressed_keycodes

    @property
    def modifier_state(self):
        return self._engine.modifier_state

    def _call(self, name, *args):
        try:
            return getattr(self._engine, name)(*args)
        except Exception as error:
            raise NativeInputError(str(error))

    def open(self, device_path):
        return self._call("open", device_path)

    def install_keymap(self, keymap_utf8):
        return self._call("install_keymap", keymap_utf8)

    def key(self, keycode, pressed, timestamp_ms):
        return self._call("key", keycode, pressed, timestamp_ms)

    def modifiers(self, depressed, latched, locked, group):
        return self._call("modifiers", depressed, latched, locked, group)

    def close(self):
        return self._call("close")


class FallbackInputEngine(object):
    """Pure-Python reference implementation of the Rust milestone contract."""

    transport = "python-fallback"

    def __init__(self):
        self._opened = False
        self._device_path = None
        self._keymap = None
        self._pressed = set()
        self._modifiers = (0, 0, 0, 0)

    @property
    def is_open(self):
        return self._opened

    @property
    def pressed_keycodes(self):
        return sorted(self._pressed)

    @property
    def modifier_state(self):
        return self._modifiers

    def open(self, device_path):
        device_path = str(device_path).strip()
        if not device_path:
            raise NativeInputError("invalid-device-path")
        self._opened = True
        self._device_path = device_path

    def install_keymap(self, keymap_utf8):
        try:
            keymap = bytes(keymap_utf8)
        except (TypeError, ValueError):
            raise NativeInputError("invalid-keymap:not-bytes")
        if not keymap:
            raise NativeInputError("invalid-keymap:empty")
        if len(keymap) > MAX_KEYMAP_BYTES:
            raise NativeInputError("invalid-keymap:too-large")
        if b"\x00" in keymap:
            raise NativeInputError("invalid-keymap:contains-nul")
        try:
            keymap.decode("utf-8")
        except UnicodeDecodeError:
            raise NativeInputError("invalid-keymap:not-utf8")
        self._keymap = keymap

    def key(self, keycode, pressed, timestamp_ms):
        del timestamp_ms
        if not self._opened:
            raise NativeInputError("engine-not-open")
        if self._keymap is None:
            raise NativeInputError("keymap-not-installed")
        keycode = int(keycode)
        if keycode < 0 or keycode > MAX_KEYCODE:
            raise NativeInputError("invalid-keycode:{}".format(keycode))
        if pressed:
            self._pressed.add(keycode)
        else:
            self._pressed.discard(keycode)

    def modifiers(self, depressed, latched, locked, group):
        self._modifiers = tuple(int(value) for value in
                                (depressed, latched, locked, group))

    def close(self):
        self._opened = False
        self._device_path = None
        self._keymap = None
        self._pressed.clear()
        self._modifiers = (0, 0, 0, 0)


def create_input_engine(mode=None):
    """Create the selected validation engine without affecting production I/O."""
    status = get_status(mode)
    if status.selected == "rust-validation":
        module, _detail = _load_native_module()
        return RustInputEngine(module)
    if status.requested == "native":
        raise NativeInputUnavailable("native-extension-unavailable:{}"
                                     .format(status.detail or "not-built"))
    return FallbackInputEngine()
