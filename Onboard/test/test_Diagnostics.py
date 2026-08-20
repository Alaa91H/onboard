# -*- coding: utf-8 -*-

import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

from Onboard import Diagnostics


class TestDiagnostics(unittest.TestCase):

    def test_collect_reports_session_and_safe_fallback(self):
        report = Diagnostics.collect({
            "XDG_SESSION_TYPE": "wayland",
            "XDG_CURRENT_DESKTOP": "GNOME",
            "ONBOARD_DIAGNOSTIC_SYSTEM": "Linux",
            "ONBOARD_DIAGNOSTIC_MACHINE": "aarch64",
            "ONBOARD_NATIVE_INPUT": "fallback",
        })
        self.assertEqual(1, report["schema"])
        self.assertEqual("onboard-classic", report["application"])
        self.assertEqual("linux", report["platform"]["platform"])
        self.assertEqual("arm64", report["platform"]["architecture"])
        self.assertEqual("wayland", report["session"]["type"])
        self.assertEqual("GNOME", report["session"]["desktop"])
        self.assertEqual("gnome-extension", report["input_source"]["strategy"])
        self.assertEqual("extension-required", report["input_source"]["state"])
        self.assertEqual("python-fallback", report["native_input"]["selected"])

    def test_render_is_valid_json_with_a_trailing_newline(self):
        rendered = Diagnostics.render({
            "ONBOARD_DIAGNOSTIC_SYSTEM": "Windows",
            "ONBOARD_DIAGNOSTIC_MACHINE": "AMD64",
        })
        self.assertTrue(rendered.endswith("\n"))
        report = json.loads(rendered)
        self.assertEqual("windows", report["platform"]["platform"])
        self.assertEqual("x64", report["platform"]["architecture"])
        self.assertEqual("not-built", report["platform"]["bridge_state"])

    def test_launcher_diagnose_avoids_gtk_startup(self):
        root = Path(__file__).resolve().parents[2]
        environment = os.environ.copy()
        environment.pop("DISPLAY", None)
        environment.pop("WAYLAND_DISPLAY", None)
        environment["ONBOARD_DIAGNOSTIC_SYSTEM"] = "Darwin"
        environment["ONBOARD_DIAGNOSTIC_MACHINE"] = "arm64"
        result = subprocess.run(
            [sys.executable, str(root / "onboard"), "--diagnose"],
            cwd=str(root), env=environment, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        report = json.loads(result.stdout)
        self.assertEqual("macos", report["platform"]["platform"])
        self.assertEqual("arm64", report["platform"]["architecture"])
        self.assertEqual("unknown", report["session"]["type"])
        self.assertEqual("unavailable", report["input_source"]["state"])
        self.assertEqual("", result.stderr)
