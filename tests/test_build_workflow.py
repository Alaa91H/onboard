"""Contract tests for the unified build entry point and its CI integration."""

from __future__ import annotations

import importlib.util
import io
import platform
import py_compile
import re
import tempfile
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
WINDOWS_INSTALLER_RECIPE = (
    REPOSITORY_ROOT / "packaging" / "windows" / "onboard-next-preview.iss"
)
WINDOWS_PREVIEW_WORKFLOW = (
    REPOSITORY_ROOT / ".github" / "workflows" / "onboard-next-preview.yml"
)
QUALITY_WORKFLOW = (
    REPOSITORY_ROOT / ".github" / "workflows" / "unified-build-quality.yml"
)
CENTRAL_CI_WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"
REUSABLE_WORKFLOWS = ("unified-build-quality.yml", *WORKFLOW_CONTRACTS)
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
LEGACY_BUILD_WRAPPERS = (
    "ci/scripts/build_linux_release_candidate.sh",
    "ci/scripts/build_debian_release_candidate.sh",
    "ci/scripts/build_rpm_release_candidate.sh",
    "ci/scripts/build_arch_release_candidate.sh",
    "ci/scripts/build_flatpak_release_candidate.sh",
    "packaging/windows/build-preview.ps1",
    "packaging/macos/build-preview.sh",
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

    def test_checksums_use_repository_relative_paths(self) -> None:
        with tempfile.TemporaryDirectory(dir=REPOSITORY_ROOT) as temporary_directory:
            output = Path(temporary_directory)
            artifact = output / "artifact.bin"
            artifact.write_bytes(b"onboard")
            self.build.write_checksums(output)
            checksum = (output / "SHA256SUMS").read_text(encoding="ascii")
        self.assertIn(f"{output.name}/artifact.bin", checksum)

    def test_declared_version_matches_project_metadata(self) -> None:
        project = (REPOSITORY_ROOT / "pyproject.toml").read_text(encoding="utf-8")
        expected = re.search(r'^\s*version\s*=\s*"([^"]+)"\s*$', project, re.MULTILINE)
        self.assertIsNotNone(expected)
        assert expected is not None
        self.assertEqual(self.build.declared_version(), expected.group(1))

    def test_all_candidate_backends_are_explicit_and_wrappers_are_removed(self) -> None:
        self.assertEqual(
            set(self.build.CANDIDATE_BACKENDS),
            {"linux", "debian", "rpm", "arch", "flatpak"},
        )
        for wrapper in LEGACY_BUILD_WRAPPERS:
            self.assertFalse((REPOSITORY_ROOT / wrapper).exists(), wrapper)

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

    def test_windows_preview_installer_contract_is_pinned(self) -> None:
        recipe = WINDOWS_INSTALLER_RECIPE.read_text(encoding="utf-8")
        workflow = WINDOWS_PREVIEW_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('#define AppName "Onboard Next"', recipe)
        self.assertIn("OutputBaseFilename=onboard-next-preview-", recipe)
        self.assertIn("ArchitecturesAllowed=", recipe)
        self.assertIn("PrivilegesRequired=lowest", recipe)
        self.assertIn("postinstall", recipe)
        self.assertIn("choco install innosetup --version=6.7.1", workflow)
        self.assertIn("-setup.exe", workflow)
        self.assertIn("installer checksum mismatch", workflow)

    def test_workflow_orchestrator_is_the_only_event_entry_point(self) -> None:
        content = CENTRAL_CI_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("pull_request:\n", content)
        self.assertIn("push:\n    branches: [main]", content)
        self.assertIn("workflow_dispatch:\n", content)
        self.assertIn("contents: read", content)
        self.assertNotIn("contents: write", content)
        self.assertIn("needs: quality", content)
        for filename in REUSABLE_WORKFLOWS:
            self.assertIn(f"uses: ./.github/workflows/{filename}", content)

        workflow_root = REPOSITORY_ROOT / ".github" / "workflows"
        for filename in REUSABLE_WORKFLOWS:
            child = (workflow_root / filename).read_text(encoding="utf-8")
            self.assertIn("workflow_call:\n", child, filename)
            self.assertNotIn("\n  pull_request:", child, filename)
            self.assertNotIn("\n  push:", child, filename)
            self.assertNotIn("\n  workflow_dispatch:", child, filename)

    def test_quality_gate_is_strict_and_read_only(self) -> None:
        content = QUALITY_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("workflow_call:\n", content)
        self.assertIn("actions/setup-python@v6", content)
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
