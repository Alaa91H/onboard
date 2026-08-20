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

"""Platform-neutral bridge capability reporting.

This module deliberately does not synthesize input. It lets the independent
application select a supported platform adapter or present a translated,
actionable state instead of silently attempting a Linux-only implementation on
Windows or macOS.
"""

from __future__ import division, print_function, unicode_literals

import platform as _platform
from collections import namedtuple


PlatformCapabilities = namedtuple(
    "PlatformCapabilities",
    "platform architecture application input_injection input_source "
    "quick_access bridge_state detail_code")


_ARCHITECTURES = {
    "x86_64": "x64",
    "amd64": "x64",
    "x64": "x64",
    "aarch64": "arm64",
    "arm64": "arm64",
    "armv8": "arm64",
}


def normalize_architecture(machine=None):
    """Return a stable release architecture label from a system machine value."""
    value = (machine or _platform.machine() or "unknown").lower()
    return _ARCHITECTURES.get(value, value)


def normalize_platform(system=None):
    """Return the stable platform identifier used by bridge and release code."""
    value = (system or _platform.system() or "unknown").lower()
    if value in ("linux", "gnu/linux"):
        return "linux"
    if value in ("windows", "cygwin", "msys"):
        return "windows"
    if value in ("darwin", "macos", "mac os x"):
        return "macos"
    return value


def get_capabilities(system=None, machine=None):
    """Describe the bridge actually present for a platform, never a future one."""
    target = normalize_platform(system)
    architecture = normalize_architecture(machine)

    if target == "linux":
        return PlatformCapabilities(
            platform="linux", architecture=architecture,
            application="onboard-classic",
            input_injection="capability-gated",
            input_source="desktop-adapter",
            quick_access="indicator-or-desktop-action",
            bridge_state="available",
            detail_code="linux-classic-bridge")

    if target == "windows":
        return PlatformCapabilities(
            platform="windows", architecture=architecture,
            application="onboard-next-required",
            input_injection="unavailable",
            input_source="unavailable",
            quick_access="unavailable",
            bridge_state="not-built",
            detail_code="windows-bridge-not-built")

    if target == "macos":
        return PlatformCapabilities(
            platform="macos", architecture=architecture,
            application="onboard-next-required",
            input_injection="unavailable",
            input_source="unavailable",
            quick_access="unavailable",
            bridge_state="not-built",
            detail_code="macos-bridge-not-built")

    return PlatformCapabilities(
        platform=target, architecture=architecture,
        application="unsupported", input_injection="unavailable",
        input_source="unavailable", quick_access="unavailable",
        bridge_state="unsupported", detail_code="unsupported-platform")
