#!/usr/bin/env python3
"""Unified, host-native build entry point for Onboard.

This command is the public build surface for local development and CI.  It
preserves package-manager-native recipes as backends while presenting one
consistent command vocabulary for source builds, release candidates and native
previews.
"""

from __future__ import annotations

import argparse
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
FOCUSED_TESTS = (
    "Onboard.test.test_WaylandCapabilities",
    "Onboard.test.test_ClipboardHistory",
    "Onboard.test.test_InputSources",
    "Onboard.test.test_LayoutLoaderSVG",
    "Onboard.test.test_QuickAccess",
    "Onboard.test.test_ArabicLocalization",
    "Onboard.test.test_NativeInput",
    "Onboard.test.test_RTL",
    "Onboard.test.test_PlatformBridge",
    "Onboard.test.test_Diagnostics",
)
CANDIDATE_BACKENDS = {
    "linux": "ci/scripts/build_linux_release_candidate.sh",
    "debian": "ci/scripts/build_debian_release_candidate.sh",
    "rpm": "ci/scripts/build_rpm_release_candidate.sh",
    "arch": "ci/scripts/build_arch_release_candidate.sh",
    "flatpak": "ci/scripts/build_flatpak_release_candidate.sh",
}


class BuildError(RuntimeError):
    """An actionable build contract violation."""


def log(message: str) -> None:
    print(f"[onboard-build] {message}", flush=True)


def run(command: Sequence[str], *, cwd: Path = ROOT) -> None:
    log("$ " + " ".join(command))
    subprocess.run(command, cwd=str(cwd), check=True)


def require_host(system: str) -> None:
    actual = platform.system().lower()
    if actual != system:
        raise BuildError(f"This command requires {system}, but the current host is {actual}.")


def declared_version() -> str:
    project_file = ROOT / "pyproject.toml"
    match = re.search(
        r'^\s*version\s*=\s*"([^"]+)"\s*$',
        project_file.read_text(encoding="utf-8"),
        flags=re.MULTILINE,
    )
    if not match:
        raise BuildError(f"Unable to read the project version from {project_file}.")
    return match.group(1)


def resolved_version(requested: str | None) -> str:
    version = declared_version()
    if requested and requested != version:
        raise BuildError(
            f"Requested version {requested!r} does not match declared version {version!r}."
        )
    return version


def detected_architecture() -> str:
    machine = platform.machine().lower()
    aliases = {
        "x86_64": "x64",
        "amd64": "x64",
        "aarch64": "arm64",
        "arm64": "arm64",
    }
    return aliases.get(machine, machine)


def require_tool(name: str) -> str:
    executable = shutil.which(name)
    if not executable:
        raise BuildError(f"Required tool {name!r} was not found on PATH.")
    return executable


def command_doctor(_: argparse.Namespace) -> None:
    log(f"repository={ROOT}")
    log(f"platform={platform.system().lower()}")
    log(f"architecture={detected_architecture()}")
    log(f"version={declared_version()}")
    tools = ("cargo", "rustc", "xvfb-run", "dpkg-buildpackage", "rpmbuild", "makepkg", "flatpak-builder")
    for tool in tools:
        print(f"{tool}={'available' if shutil.which(tool) else 'missing'}")


def verify_portable_artifacts() -> None:
    wheels = sorted((ROOT / "dist").glob("*.whl"))
    sdists = sorted((ROOT / "dist").glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise BuildError("Expected exactly one wheel and one source archive in dist/.")

    with zipfile.ZipFile(wheels[0]) as archive:
        names = archive.namelist()
    if not any(re.fullmatch(r"Onboard/onboard_native.*\.(so|pyd)", name) for name in names):
        raise BuildError("The wheel does not contain the native Onboard extension.")
    if not any(name.endswith("share/locale/ar/LC_MESSAGES/onboard.mo") for name in names):
        raise BuildError("The wheel does not contain the compiled Arabic catalog.")

    with tarfile.open(sdists[0], "r:gz") as archive:
        source_names = archive.getnames()
    if not any(name.endswith("native/onboard-native/Cargo.lock") for name in source_names):
        raise BuildError("The source archive does not contain the locked native Cargo dependencies.")


def command_portable(args: argparse.Namespace) -> None:
    require_host("linux")
    if args.prepare:
        run(["bash", "tools/prepare-build-env.sh", "--with-tests"])
    require_tool("xvfb-run")
    run([sys.executable, "setup.py", "build"])
    run(["xvfb-run", "-a", sys.executable, "-m", "unittest", *FOCUSED_TESTS])
    run(["cargo", "test", "--locked"], cwd=ROOT / "native/onboard-native")
    run([sys.executable, "i18n/scripts/check_catalog.py", "po/ar.po", "--language", "ar", "--require-complete"])
    run([sys.executable, "-m", "build", "--no-isolation"])
    verify_portable_artifacts()
    log("Portable source build and verification completed successfully.")


def command_native(args: argparse.Namespace) -> None:
    require_tool("cargo")
    native_root = ROOT / "native/onboard-native"
    if args.check_only:
        run(["cargo", "check", "--tests", "--locked"], cwd=native_root)
    else:
        run(["cargo", "test", "--locked"], cwd=native_root)
    run(["cargo", "build", "--release", "--locked"], cwd=native_root)
    log("Native Rust bridge verification completed successfully.")


def command_candidate(args: argparse.Namespace) -> None:
    backend = CANDIDATE_BACKENDS[args.target]
    version = resolved_version(args.version)
    require_tool("bash")
    run(["bash", backend, args.arch, version])
    output = ROOT / "release-out" / f"{args.target}-{args.arch}"
    if args.target == "linux":
        output = ROOT / "release-out" / f"linux-{args.arch}"
    if not output.is_dir():
        raise BuildError(f"Candidate backend completed without creating {output}.")
    log(f"Verified {args.target} candidate written to {output.relative_to(ROOT)}.")


def command_preview(args: argparse.Namespace) -> None:
    version = args.version or "0.1.0"
    if args.platform == "windows":
        require_host("windows")
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if not powershell:
            raise BuildError("PowerShell is required for the Windows preview backend.")
        run([
            powershell,
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "packaging/windows/build-preview.ps1",
            "-Architecture",
            args.arch,
            "-Version",
            version,
        ])
    else:
        require_host("darwin")
        require_tool("bash")
        run(["bash", "packaging/macos/build-preview.sh", args.arch, version])
    log(f"{args.platform} preview completed for {args.arch}.")


def command_validate_recipes(_: argparse.Namespace) -> None:
    require_tool("bash")
    run(["bash", "-n", "packaging/arch/PKGBUILD"])
    manifest = ROOT / "packaging/flatpak/org.onboard.Onboard.yml"
    content = manifest.read_text(encoding="utf-8")
    required_markers = (
        "id: org.onboard.Onboard",
        "runtime: org.gnome.Platform",
        "command: onboard",
        "org.freedesktop.Sdk.Extension.rust-stable",
    )
    missing = [marker for marker in required_markers if marker not in content]
    if missing:
        raise BuildError("Flatpak manifest is missing: " + ", ".join(missing))
    required_files = (
        ROOT / "native/onboard-native/Cargo.lock",
        ROOT / "native/onboard-native/.cargo/config.toml",
        ROOT / "packaging/flatpak/intltool-perl5.26-regex-fixes.patch",
    )
    absent = [str(path.relative_to(ROOT)) for path in required_files if not path.is_file()]
    if absent:
        raise BuildError("Required package assets are missing: " + ", ".join(absent))
    log("Package recipe validation completed successfully.")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description="Unified host-native build, package, preview and validation interface for Onboard."
    )
    subparsers = root.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser("doctor", help="Report host capabilities and declared project version.")
    doctor.set_defaults(handler=command_doctor)

    portable = subparsers.add_parser("portable", help="Build and verify portable Linux wheel and source artifacts.")
    portable.add_argument("--prepare", action="store_true", help="Install host build prerequisites before building.")
    portable.set_defaults(handler=command_portable)

    native = subparsers.add_parser("native", help="Verify and build the native Rust bridge on the current host.")
    native.add_argument("--check-only", action="store_true", help="Use cargo check for tests before the release build.")
    native.set_defaults(handler=command_native)

    candidate = subparsers.add_parser("candidate", help="Build a native release candidate using the selected package backend.")
    candidate.add_argument("target", choices=sorted(CANDIDATE_BACKENDS), help="Candidate artifact family.")
    candidate.add_argument("--arch", choices=("x64", "arm64"), default=detected_architecture(), help="Native target architecture.")
    candidate.add_argument("--version", help="Optional exact version guard; defaults to pyproject.toml.")
    candidate.set_defaults(handler=command_candidate)

    preview = subparsers.add_parser("preview", help="Build a host-native unsigned onboard-next preview.")
    preview.add_argument("platform", choices=("windows", "macos"), help="Native preview platform.")
    preview.add_argument("--arch", choices=("x64", "arm64"), default=detected_architecture(), help="Native target architecture.")
    preview.add_argument("--version", help="Preview version; defaults to 0.1.0.")
    preview.set_defaults(handler=command_preview)

    recipes = subparsers.add_parser("validate-recipes", help="Validate static package recipe contracts.")
    recipes.set_defaults(handler=command_validate_recipes)
    return root


def main(argv: Iterable[str] | None = None) -> int:
    arguments = parser().parse_args(list(argv) if argv is not None else None)
    try:
        arguments.handler(arguments)
    except BuildError as error:
        print(f"[onboard-build] error: {error}", file=sys.stderr)
        return 2
    except subprocess.CalledProcessError as error:
        print(f"[onboard-build] command failed with exit code {error.returncode}.", file=sys.stderr)
        return error.returncode or 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
