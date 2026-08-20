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

"""Non-invasive runtime diagnostics for the independent Onboard application.

The functions here deliberately avoid GTK, D-Bus, compositor protocols, and
input injection. They are safe to call in bug reports or before a graphical
session is fully available. Values are stable machine-readable codes; the UI
may translate those codes separately when it presents them to the user.
"""

from __future__ import division, print_function, unicode_literals

import json
import os

from Onboard import NativeInput, PlatformBridge


SCHEMA_VERSION = 1


def _session_type(environ):
    session = environ.get("XDG_SESSION_TYPE", "").strip().lower()
    if session in ("wayland", "x11"):
        return session
    if environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if environ.get("DISPLAY"):
        return "x11"
    return "unknown"


def _desktop(environ):
    value = (environ.get("XDG_CURRENT_DESKTOP") or
             environ.get("XDG_SESSION_DESKTOP") or
             environ.get("DESKTOP_SESSION") or "unknown")
    return value


def _input_source_capability(session_type, desktop):
    """Describe the selectable input-source route without opening a backend."""
    desktop_upper = desktop.upper()
    if session_type == "x11":
        return {"strategy": "x11", "state": "session-required"}
    if session_type == "wayland" and ("KDE" in desktop_upper or
                                       "PLASMA" in desktop_upper):
        return {"strategy": "kde-dbus", "state": "session-required"}
    if session_type == "wayland" and "GNOME" in desktop_upper:
        return {"strategy": "gnome-extension",
                "state": "extension-required"}
    if session_type == "wayland":
        return {"strategy": "none", "state": "read-only"}
    return {"strategy": "none", "state": "unavailable"}


def _as_dict(value):
    """Convert the project's namedtuple and dataclass state records safely."""
    if hasattr(value, "_fields"):
        return {key: getattr(value, key) for key in value._fields}
    if hasattr(value, "__dataclass_fields__"):
        return {key: getattr(value, key)
                for key in value.__dataclass_fields__}
    raise TypeError("unsupported diagnostics record: {}".format(type(value)))


def collect(environ=None, native_mode=None):
    """Collect a serializable capability report without opening a window."""
    environ = os.environ if environ is None else environ
    if native_mode is None:
        native_mode = environ.get("ONBOARD_NATIVE_INPUT")
    platform_state = PlatformBridge.get_capabilities(
        system=environ.get("ONBOARD_DIAGNOSTIC_SYSTEM"),
        machine=environ.get("ONBOARD_DIAGNOSTIC_MACHINE"))
    native_state = NativeInput.get_status(native_mode)

    session_type = _session_type(environ)
    desktop = _desktop(environ)
    return {
        "schema": SCHEMA_VERSION,
        "application": "onboard-classic",
        "platform": _as_dict(platform_state),
        "native_input": _as_dict(native_state),
        "input_source": _input_source_capability(session_type, desktop),
        "session": {
            "type": session_type,
            "desktop": desktop,
            "backend_requested": environ.get("ONBOARD_BACKEND", "auto"),
            "xwayland_forced": environ.get("ONBOARD_FORCED_XWAYLAND") == "1",
            "xwayland_auto": environ.get("ONBOARD_AUTO_XWAYLAND") == "1",
        },
    }


def render(environ=None, native_mode=None):
    """Return an indented JSON report with a trailing newline."""
    return json.dumps(collect(environ, native_mode), ensure_ascii=False,
                      indent=2, sort_keys=True) + "\n"
