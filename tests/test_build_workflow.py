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
LEGACY_WORKFLOWS = (
    "distribution-packages.yml",
    "onboard-next-preview.yml",
    "platform-native.yml",
    "portable-build.yml",
    "release-candidate.yml",
    "unified-build-quality.yml",
)
WINDOWS_INSTALLER_RECIPE = (
    REPOSITORY_ROOT / "packaging" / "windows" / "onboard-next-preview.iss"
)
CENTRAL_CI_WORKFLOW = REPOSITORY_ROOT / ".github" / "workflows" / "ci.yml"
WINDOWS_PREVIEW_WORKFLOW = CENTRAL_CI_WORKFLOW
WORKFLOW_ROOT = REPOSITORY_ROOT / ".github" / "workflows"
WINDOWS_APP_MANIFEST = (
    REPOSITORY_ROOT / "next" / "crates" / "onboard-next" / "Cargo.toml"
)
WINDOWS_APP_ENTRYPOINT = (
    REPOSITORY_ROOT / "next" / "crates" / "onboard-next" / "src" / "main.rs"
)
WINDOWS_TRAY_SOURCE = (
    REPOSITORY_ROOT / "next" / "crates" / "onboard-next" / "src" / "windows_tray.rs"
)
WINDOWS_UPDATER_SOURCE = (
    REPOSITORY_ROOT / "next" / "crates" / "onboard-next" / "src" / "windows_update.rs"
)
WINDOWS_INSTANCE_SOURCE = (
    REPOSITORY_ROOT / "next" / "crates" / "onboard-next" / "src" / "windows_instance.rs"
)
WINDOWS_ARABIC_FONT = (
    REPOSITORY_ROOT
    / "next"
    / "crates"
    / "onboard-next"
    / "assets"
    / "fonts"
    / "NotoSansArabic-Variable.ttf"
)
ALL_CATALOG_CHECKER = REPOSITORY_ROOT / "i18n" / "scripts" / "check_all_catalogs.py"
I18N_MODULE = REPOSITORY_ROOT / "Onboard" / "I18n.py"
QUALITY_GATE_COMMANDS = (
    "sudo apt-get update && sudo apt-get install --yes gettext",
    "python -m py_compile tools/build.py tests/test_build_workflow.py",
    "ruff check tools/build.py tests/test_build_workflow.py",
    "ruff format --check tools/build.py tests/test_build_workflow.py",
    "mypy --strict tools/build.py tests/test_build_workflow.py",
    "python -m py_compile i18n/scripts/check_all_catalogs.py",
    "i18n/scripts/normalize_locale_headers.py Onboard/I18n.py",
    "ruff check i18n/scripts/check_all_catalogs.py i18n/scripts/normalize_locale_headers.py",
    "ruff format --check i18n/scripts/check_all_catalogs.py i18n/scripts/normalize_locale_headers.py",
    "mypy --strict i18n/scripts/check_all_catalogs.py i18n/scripts/normalize_locale_headers.py",
    "python -m unittest discover -s tests -v",
    "yamllint -c .yamllint .github/workflows",
    "git diff --check",
    "python tools/build.py validate-recipes",
    "python tools/build.py validate-translations",
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
        translations = parser.parse_args(["validate-translations"])
        self.assertEqual(translations.command, "validate-translations")

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

    def test_windows_preview_installer_contract_is_pinned(self) -> None:
        recipe = WINDOWS_INSTALLER_RECIPE.read_text(encoding="utf-8")
        workflow = WINDOWS_PREVIEW_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn('#define AppName "Onboard Next"', recipe)
        self.assertIn("OutputBaseFilename=onboard-next-preview-", recipe)
        self.assertIn("ArchitecturesAllowed=", recipe)
        self.assertIn("PrivilegesRequired=lowest", recipe)
        self.assertIn("postinstall", recipe)
        self.assertIn('Name: "startup"', recipe)
        self.assertIn("--start-minimized", recipe)
        self.assertIn("CurrentVersion\\Run", recipe)
        self.assertIn("uninsdeletevalue", recipe)
        self.assertIn("choco install innosetup --version=6.7.1", workflow)
        self.assertIn("-setup.exe", workflow)
        self.assertIn("installer checksum mismatch", workflow)

    def test_windows_tray_contract_preserves_minimize_to_notification_area(
        self,
    ) -> None:
        manifest = WINDOWS_APP_MANIFEST.read_text(encoding="utf-8")
        entrypoint = WINDOWS_APP_ENTRYPOINT.read_text(encoding="utf-8")
        tray_source = WINDOWS_TRAY_SOURCE.read_text(encoding="utf-8")
        self.assertIn('tray-icon = "=0.21.3"', manifest)
        self.assertIn("ViewportCommand::CancelClose", entrypoint)
        self.assertIn("ViewportCommand::Visible(false)", entrypoint)
        self.assertIn("ViewportCommand::Visible(true)", entrypoint)
        self.assertIn("minimized == Some(true)", entrypoint)
        self.assertIn("إظهار اللوحة", tray_source)
        self.assertIn("إخفاء إلى منطقة الإعلام", tray_source)
        self.assertIn("إنهاء Onboard Next", tray_source)

    def test_windows_startup_and_update_contract_is_safe_and_user_visible(self) -> None:
        manifest = WINDOWS_APP_MANIFEST.read_text(encoding="utf-8")
        entrypoint = WINDOWS_APP_ENTRYPOINT.read_text(encoding="utf-8")
        updater = WINDOWS_UPDATER_SOURCE.read_text(encoding="utf-8")
        self.assertIn('ureq = { version = "=2.12.1"', manifest)
        self.assertIn("START_MINIMIZED_ARGUMENT", entrypoint)
        self.assertIn("with_visible(!start_minimized)", entrypoint)
        self.assertIn("show_update_status", entrypoint)
        self.assertIn("releases/latest", updater)
        self.assertIn("CHECK_INTERVAL", updater)
        self.assertIn("start_background_check", updater)
        self.assertNotIn("std::process::Command", updater)
        self.assertNotIn("std::fs::write", updater)

    def test_windows_ui_contract_embeds_fonts_and_restores_one_instance(self) -> None:
        entrypoint = WINDOWS_APP_ENTRYPOINT.read_text(encoding="utf-8")
        instance_source = WINDOWS_INSTANCE_SOURCE.read_text(encoding="utf-8")
        self.assertTrue(WINDOWS_ARABIC_FONT.is_file())
        self.assertGreater(WINDOWS_ARABIC_FONT.stat().st_size, 500_000)
        self.assertIn("configure_fonts", entrypoint)
        self.assertIn("NotoSansArabic-Variable.ttf", entrypoint)
        self.assertIn("ui.vertical", entrypoint)
        self.assertIn("with_max_inner_size", entrypoint)
        self.assertIn("PrimaryInstance::acquire_or_show_existing", entrypoint)
        self.assertIn("CreateMutexW", instance_source)
        self.assertIn("FindWindowW", instance_source)
        self.assertIn("SW_RESTORE", instance_source)

    def test_i18n_rtl_supports_languages_and_script_subtags(self) -> None:
        spec = importlib.util.spec_from_file_location("onboard_i18n", I18N_MODULE)
        self.assertIsNotNone(spec)
        assert spec is not None and spec.loader is not None
        i18n = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(i18n)
        self.assertEqual(i18n.get_text_direction({"LANGUAGE": "ar_SA.UTF-8"}), "rtl")
        self.assertEqual(i18n.get_text_direction({"LANGUAGE": "he-IL"}), "rtl")
        self.assertEqual(i18n.get_text_direction({"LANGUAGE": "az_Arab:en_US"}), "rtl")
        self.assertEqual(i18n.get_text_direction({"LANGUAGE": "ku@arabic"}), "rtl")
        self.assertEqual(i18n.get_text_direction({"LANGUAGE": "en_US:ar"}), "ltr")

    def test_translation_validation_contract_covers_all_catalogs(self) -> None:
        build_source = BUILD_SCRIPT.read_text(encoding="utf-8")
        checker = ALL_CATALOG_CHECKER.read_text(encoding="utf-8")
        self.assertIn("check_all_catalogs.py", build_source)
        self.assertIn("--require-complete", build_source)
        self.assertIn('"ar"', build_source)
        self.assertIn("msgattrib", checker)
        self.assertIn("msgfmt", checker)
        self.assertIn("nplurals=6", checker)
        self.assertIn("format fields differ", checker)

    def test_ci_is_the_only_workflow_and_directly_owns_all_build_jobs(self) -> None:
        content = CENTRAL_CI_WORKFLOW.read_text(encoding="utf-8")
        self.assertEqual(
            sorted(path.name for path in WORKFLOW_ROOT.glob("*.yml")), ["ci.yml"]
        )
        self.assertIn("pull_request:\n", content)
        self.assertIn("push:\n    branches: [main]", content)
        self.assertIn("workflow_dispatch:\n", content)
        self.assertIn("contents: read", content)
        self.assertNotIn("contents: write", content)
        self.assertNotIn("workflow_call:", content)
        self.assertNotIn("uses: ./.github/workflows/", content)
        for legacy_workflow in LEGACY_WORKFLOWS:
            self.assertFalse(
                (WORKFLOW_ROOT / legacy_workflow).exists(), legacy_workflow
            )
        for job_name in (
            "quality:",
            "portable-ubuntu:",
            "windows-bridge:",
            "debian:",
            "rpm:",
            "arch-x64:",
            "arch-arm64:",
            "flatpak:",
            "resolve-version:",
            "linux-release-candidate:",
            "windows-preview:",
            "macos-preview:",
        ):
            self.assertIn(job_name, content)

    def test_quality_gate_is_strict_and_read_only(self) -> None:
        content = CENTRAL_CI_WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("actions/setup-python@v6", content)
        self.assertIn("contents: read", content)
        self.assertNotIn("contents: write", content)
        self.assertIn("timeout-minutes: 10", content)
        for command in QUALITY_GATE_COMMANDS:
            self.assertIn(command, content)

    def test_ci_does_not_bypass_the_unified_build_entry_point(self) -> None:
        content = CENTRAL_CI_WORKFLOW.read_text(encoding="utf-8")
        for pattern in FORBIDDEN_WORKFLOW_PATTERNS:
            self.assertNotRegex(content, pattern, f"ci.yml: {pattern}")


if __name__ == "__main__":
    unittest.main()
