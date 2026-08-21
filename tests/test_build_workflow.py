"""Contract tests for the unified build entry point and its CI integration."""

from __future__ import annotations

import importlib.util
import io
import platform
import py_compile
import re
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from types import ModuleType
from typing import ClassVar
from unittest import mock


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = REPOSITORY_ROOT / "tools" / "build.py"
WORKFLOW_CONTRACTS = {
    "portable-build.yml": "python3 tools/build.py portable",
    "release-candidate.yml": "python3 tools/build.py candidate linux",
    "distribution-packages.yml": "python3 tools/build.py candidate",
    "platform-native.yml": "tools/build.py native",
    "onboard-next-preview.yml": "tools/build.py preview",
}
QUALITY_WORKFLOW = (
    REPOSITORY_ROOT / ".github" / "workflows" / "unified-build-quality.yml"
)
QUALITY_GATE_COMMANDS = (
    "python -m py_compile tools/build.py tests/test_build_workflow.py",
    "ruff check tools/build.py tests/test_build_workflow.py",
    "ruff format --check tools/build.py tests/test_build_workflow.py",
    "mypy --strict tools/build.py tests/test_build_workflow.py",
    "python -m unittest discover -s tests -v",
    "yamllint -c .yamllint .github/workflows",
    "git diff --check",
    "python tools/build.py validate-recipes",
)
FORBIDDEN_WORKFLOW_PATTERNS = (
    r"(?:bash\s+)?ci/scripts/build_[a-z_]+release_candidate\.sh",
    r"(?:python3?\s+)?setup\.py\s+build",
    r"cargo\s+(?:test|check|build)\b.*--locked",
    r"packaging/(?:windows|macos)/build-preview\.(?:ps1|sh)",
)


def load_build_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("onboard_build", BUILD_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {BUILD_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestUnifiedBuildWorkflow(unittest.TestCase):
    build: ClassVar[ModuleType]

    @classmethod
    def setUpClass(cls) -> None:
        cls.build = load_build_module()

    def test_build_script_compiles(self) -> None:
        py_compile.compile(str(BUILD_SCRIPT), doraise=True)

    def test_declared_version_matches_project_metadata(self) -> None:
        project = (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        expected = re.search(r'^\s*version\s*=\s*"([^"]+)"\s*$', project, re.MULTILINE)
        self.assertIsNotNone(expected)
        assert expected is not None
        self.assertEqual(self.build.declared_version(), expected.group(1))

    def test_all_candidate_backends_are_explicit_and_exist(self) -> None:
        self.assertEqual(
            set(self.build.CANDIDATE_BACKENDS),
            {"linux", "debian", "rpm", "arch", "flatpak"},
        )
        for backend in self.build.CANDIDATE_BACKENDS.values():
            self.assertTrue((REPOSITORY_ROOT / backend).is_file(), backend)

    def test_parser_exposes_only_supported_architectures(self) -> None:
        parser = self.build.parser()
        linux = parser.parse_args(["candidate", "linux", "--arch", "x64"])
        self.assertEqual(linux.arch, "x64")
        self.assertEqual(linux.target, "linux")
        native = parser.parse_args(["native", "--check-only"])
        self.assertTrue(native.check_only)
        preview = parser.parse_args(["preview", "windows", "--arch", "arm64"])
        self.assertEqual(preview.platform, "windows")
        self.assertEqual(preview.arch, "arm64")

    def test_candidate_rejects_mismatched_version_before_running_backend(self) -> None:
        stderr = io.StringIO()
        with mock.patch.object(self.build, "run") as backend, redirect_stderr(stderr):
            result = self.build.main(["candidate", "linux", "--version", "0.0.0"])
        self.assertEqual(result, 2)
        backend.assert_not_called()
        self.assertIn("does not match declared version", stderr.getvalue())

    def test_preview_refuses_wrong_host_before_running_backend(self) -> None:
        current = platform.system().lower()
        target = "windows" if current != "windows" else "macos"
        with mock.patch.object(self.build, "run") as backend, redirect_stderr(
            io.StringIO()
        ):
            result = self.build.main(["preview", target])
        self.assertEqual(result, 2)
        backend.assert_not_called()

    def test_every_build_workflow_calls_the_unified_entry_point(self) -> None:
        workflow_root = REPOSITORY_ROOT / ".github" / "workflows"
        for filename, required_command in WORKFLOW_CONTRACTS.items():
            content = (workflow_root / filename).read_text(encoding="utf-8")
            self.assertIn("tools/build.py", content, filename)
            self.assertIn(required_command, content, filename)

    def test_quality_gate_is_strict_read_only_and_pull_request_wide(self) -> None:
        content = QUALITY_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("pull_request:\n", content)
        self.assertIn("contents: read", content)
        self.assertNotIn("contents: write", content)
        self.assertIn("timeout-minutes: 10", content)
        for command in QUALITY_GATE_COMMANDS:
            self.assertIn(command, content)

    def test_workflows_do_not_bypass_unified_entry_point(self) -> None:
        workflow_root = REPOSITORY_ROOT / ".github" / "workflows"
        for workflow in workflow_root.glob("*.yml"):
            content = workflow.read_text(encoding="utf-8")
            for pattern in FORBIDDEN_WORKFLOW_PATTERNS:
                self.assertNotRegex(content, pattern, f"{workflow.name}: {pattern}")


if __name__ == "__main__":
    unittest.main()
