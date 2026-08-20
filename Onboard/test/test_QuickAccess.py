#!/usr/bin/python3

import os
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOGGLE = ROOT / "onboard-toggle"
DESKTOP = ROOT / "data" / "onboard.desktop.in"
SCHEMA = ROOT / "data" / "org.onboard.gschema.xml"


class TestQuickAccess(unittest.TestCase):

    def test_desktop_entry_exposes_a_toggle_action(self):
        content = DESKTOP.read_text(encoding="utf-8")
        self.assertIn("Actions=Toggle;", content)
        self.assertIn("[Desktop Action Toggle]", content)
        self.assertIn("Exec=onboard-toggle", content)

    def test_status_icon_defaults_to_direct_toggle(self):
        content = SCHEMA.read_text(encoding="utf-8")
        start = content.index('<key name="status-icon-left-click-action"')
        end = content.index("</key>", start)
        self.assertIn('<default>"toggle"</default>', content[start:end])

    def test_toggle_command_uses_existing_dbus_service(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            marker = temp / "onboard-started"
            self._write_executable(temp / "gdbus", "#!/bin/sh\nexit 0\n")
            self._write_executable(
                temp / "onboard",
                "#!/bin/sh\nprintf started > \"$ONBOARD_TEST_MARKER\"\n")
            result = self._run_toggle(temp, marker)
            self.assertEqual(0, result.returncode)
            self.assertFalse(marker.exists())

    def test_toggle_command_launches_when_service_is_absent(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            marker = temp / "onboard-started"
            self._write_executable(temp / "gdbus", "#!/bin/sh\nexit 1\n")
            self._write_executable(
                temp / "onboard",
                "#!/bin/sh\nprintf started > \"$ONBOARD_TEST_MARKER\"\n")
            result = self._run_toggle(temp, marker)
            self.assertEqual(0, result.returncode)
            self.assertEqual("started", marker.read_text(encoding="utf-8"))

    @staticmethod
    def _write_executable(path, content):
        path.write_text(content, encoding="utf-8")
        path.chmod(0o755)

    @staticmethod
    def _run_toggle(bin_dir, marker):
        environment = os.environ.copy()
        environment["PATH"] = "{}:{}".format(bin_dir, environment["PATH"])
        environment["ONBOARD_TEST_MARKER"] = str(marker)
        return subprocess.run([str(TOGGLE)], env=environment,
                              capture_output=True, text=True, check=False)
