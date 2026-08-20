# -*- coding: utf-8 -*-

import unittest

from Onboard import PlatformBridge


class TestPlatformBridge(unittest.TestCase):

    def test_normalizes_supported_architecture_names(self):
        self.assertEqual("x64", PlatformBridge.normalize_architecture("x86_64"))
        self.assertEqual("x64", PlatformBridge.normalize_architecture("AMD64"))
        self.assertEqual("arm64", PlatformBridge.normalize_architecture("aarch64"))
        self.assertEqual("arm64", PlatformBridge.normalize_architecture("ARM64"))

    def test_normalizes_platform_names(self):
        self.assertEqual("linux", PlatformBridge.normalize_platform("Linux"))
        self.assertEqual("windows", PlatformBridge.normalize_platform("Windows"))
        self.assertEqual("macos", PlatformBridge.normalize_platform("Darwin"))

    def test_linux_reports_the_current_capability_gated_bridge(self):
        result = PlatformBridge.get_capabilities("Linux", "x86_64")
        self.assertEqual("linux", result.platform)
        self.assertEqual("x64", result.architecture)
        self.assertEqual("onboard-classic", result.application)
        self.assertEqual("available", result.bridge_state)
        self.assertEqual("capability-gated", result.input_injection)

    def test_windows_is_explicitly_not_available_until_native_app_exists(self):
        result = PlatformBridge.get_capabilities("Windows", "ARM64")
        self.assertEqual("windows", result.platform)
        self.assertEqual("arm64", result.architecture)
        self.assertEqual("onboard-next-required", result.application)
        self.assertEqual("not-built", result.bridge_state)
        self.assertEqual("windows-bridge-not-built", result.detail_code)

    def test_macos_is_explicitly_not_available_until_native_app_exists(self):
        result = PlatformBridge.get_capabilities("Darwin", "arm64")
        self.assertEqual("macos", result.platform)
        self.assertEqual("not-built", result.bridge_state)
        self.assertEqual("macos-bridge-not-built", result.detail_code)

    def test_unknown_platform_is_not_claimed_as_supported(self):
        result = PlatformBridge.get_capabilities("FreeBSD", "x86_64")
        self.assertEqual("freebsd", result.platform)
        self.assertEqual("unsupported", result.bridge_state)
        self.assertEqual("unsupported-platform", result.detail_code)
