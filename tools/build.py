#!/usr/bin/env python3
"""Unified, host-native build entry point for Onboard.

This is the only executable build interface for source artifacts, package
candidates, native bridge validation and Windows/macOS previews. Distribution
recipes remain declarative inputs because Debian, RPM, Arch and Flatpak require
those native formats, but no wrapper build scripts are used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import plistlib
import re
import shutil
import subprocess
import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Callable, Iterable, Sequence


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
CANDIDATE_BACKENDS = ("linux", "debian", "rpm", "arch", "flatpak")
ARCHITECTURES = ("x64", "arm64")


class BuildError(RuntimeError):
    """An actionable build contract violation."""


def log(message: str) -> None:
    print(f"[onboard-build] {message}", flush=True)


def run(command: Sequence[str], *, cwd: Path = ROOT) -> None:
    log("$ " + " ".join(command))
    subprocess.run(command, cwd=str(cwd), check=True)


def capture(command: Sequence[str], *, cwd: Path = ROOT) -> str:
    log("$ " + " ".join(command))
    completed = subprocess.run(
        command,
        cwd=str(cwd),
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    return completed.stdout.strip()


def require_host(system: str) -> None:
    actual = platform.system().lower()
    if actual != system:
        raise BuildError(
            f"This command requires {system}, but the current host is {actual}."
        )


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


def require_architecture(expected: str) -> None:
    actual = detected_architecture()
    if actual != expected:
        raise BuildError(
            f"This command requires native architecture {expected}, but the host is {actual}."
        )


def require_tool(name: str) -> str:
    executable = shutil.which(name)
    if not executable:
        raise BuildError(f"Required tool {name!r} was not found on PATH.")
    return executable


def require_file(path: Path) -> None:
    if not path.is_file():
        raise BuildError(f"Required file is missing: {path.relative_to(ROOT)}.")


def clean_paths(*paths: Path) -> None:
    for path in paths:
        if path.is_dir():
            shutil.rmtree(path)
        elif path.exists():
            path.unlink()


def remove_matches(directory: Path, pattern: str) -> None:
    for path in directory.glob(pattern):
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def copy_file(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_checksums(directory: Path, *, recursive: bool = False) -> None:
    paths = directory.rglob("*") if recursive else directory.glob("*")
    files = sorted(
        path for path in paths if path.is_file() and path.name != "SHA256SUMS"
    )
    if not files:
        raise BuildError(
            f"No artifacts were found for checksum generation in {directory}."
        )
    lines = [f"{sha256(path)}  {path.relative_to(ROOT)}" for path in files]
    (directory / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="ascii")


def write_candidate_metadata(
    output: Path,
    *,
    target_os: str,
    arch: str,
    version: str,
) -> None:
    run(
        [
            sys.executable,
            "ci/scripts/write_sbom.py",
            "--output",
            str(output / "sbom.cdx.json"),
            "--version",
            version,
        ]
    )
    run(
        [
            sys.executable,
            "ci/scripts/write_release_manifest.py",
            "--input",
            str(output),
            "--output",
            str(output / "release-manifest.json"),
            "--target-os",
            target_os,
            "--target-arch",
            arch,
            "--version",
            version,
        ]
    )
    write_checksums(output)


def verify_portable_artifacts() -> tuple[Path, Path]:
    wheels = sorted((ROOT / "dist").glob("*.whl"))
    sdists = sorted((ROOT / "dist").glob("*.tar.gz"))
    if len(wheels) != 1 or len(sdists) != 1:
        raise BuildError("Expected exactly one wheel and one source archive in dist/.")

    with zipfile.ZipFile(wheels[0]) as archive:
        names = archive.namelist()
    if not any(
        re.fullmatch(r"Onboard/onboard_native.*\.(so|pyd)", name) for name in names
    ):
        raise BuildError("The wheel does not contain the native Onboard extension.")
    if not any(
        name.endswith("share/locale/ar/LC_MESSAGES/onboard.mo") for name in names
    ):
        raise BuildError("The wheel does not contain the compiled Arabic catalog.")

    with tarfile.open(sdists[0], "r:gz") as archive:
        source_names = archive.getnames()
    if not any(
        name.endswith("native/onboard-native/Cargo.lock") for name in source_names
    ):
        raise BuildError(
            "The source archive does not contain the locked native Cargo dependencies."
        )
    return wheels[0], sdists[0]


def build_source_distributions() -> tuple[Path, Path]:
    run([sys.executable, "-m", "build", "--no-isolation"])
    return verify_portable_artifacts()


def command_doctor(_: argparse.Namespace) -> None:
    log(f"repository={ROOT}")
    log(f"platform={platform.system().lower()}")
    log(f"architecture={detected_architecture()}")
    log(f"version={declared_version()}")
    tools = (
        "cargo",
        "rustc",
        "xvfb-run",
        "dpkg-buildpackage",
        "rpmbuild",
        "makepkg",
        "flatpak-builder",
    )
    for tool in tools:
        print(f"{tool}={'available' if shutil.which(tool) else 'missing'}")


def command_portable(args: argparse.Namespace) -> None:
    require_host("linux")
    if args.prepare:
        run(["bash", "tools/prepare-build-env.sh", "--with-tests"])
    require_tool("xvfb-run")
    run([sys.executable, "setup.py", "build"])
    run(["xvfb-run", "-a", sys.executable, "-m", "unittest", *FOCUSED_TESTS])
    run(["cargo", "test", "--locked"], cwd=ROOT / "native/onboard-native")
    run(
        [
            sys.executable,
            "i18n/scripts/check_catalog.py",
            "po/ar.po",
            "--language",
            "ar",
            "--require-complete",
        ]
    )
    build_source_distributions()
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


def build_linux_candidate(arch: str, version: str) -> Path:
    require_host("linux")
    require_architecture(arch)
    run(["bash", "tools/prepare-build-env.sh", "--with-tests"])
    package_version = capture([sys.executable, "setup.py", "--version"]).splitlines()[
        -1
    ]
    if package_version != version:
        raise BuildError(
            f"Candidate version {version!r} does not match package version {package_version!r}."
        )

    output = ROOT / "release-out" / f"linux-{arch}"
    clean_paths(ROOT / "build", ROOT / "dist", output)
    output.mkdir(parents=True)
    command_portable(argparse.Namespace(prepare=False))
    wheel, sdist = verify_portable_artifacts()
    copy_file(wheel, output / wheel.name)
    copy_file(sdist, output / sdist.name)
    write_candidate_metadata(output, target_os="linux", arch=arch, version=version)
    return output


def build_debian_candidate(arch: str, version: str) -> Path:
    require_host("linux")
    expected_arch = {"x64": "amd64", "arm64": "arm64"}[arch]
    for tool in ("dpkg", "dpkg-buildpackage", "dpkg-deb", "dpkg-parsechangelog"):
        require_tool(tool)
    actual_arch = capture(["dpkg", "--print-architecture"])
    if actual_arch != expected_arch:
        raise BuildError(
            f"Expected Debian architecture {expected_arch}, but the host is {actual_arch}."
        )
    debian_version = capture(["dpkg-parsechangelog", "-SVersion"])
    if not debian_version.startswith(f"{version}-"):
        raise BuildError(
            f"Debian changelog version {debian_version!r} does not match {version!r}."
        )

    clean_paths(
        ROOT / "build",
        ROOT / "debian/.debhelper",
        ROOT / "debian/onboard",
        ROOT / "debian/onboard-common",
        ROOT / "debian/onboard-data",
        ROOT / "debian/gnome-shell-extension-onboard",
        ROOT / ".pybuild",
    )
    remove_matches(ROOT / "Onboard", "osk*.so")
    remove_matches(ROOT / "Onboard/pypredict", "lm*.so")
    for pattern in (
        f"onboard_{debian_version}_*.deb",
        f"onboard_{debian_version}_*.buildinfo",
        f"onboard_{debian_version}_*.changes",
    ):
        remove_matches(ROOT.parent, pattern)

    run(["dpkg-buildpackage", "-b", "-uc", "-us"])
    output = ROOT / "release-out" / f"debian-{arch}"
    clean_paths(output)
    output.mkdir(parents=True)
    packages = sorted(ROOT.parent.glob(f"onboard_{debian_version}_*.deb"))
    if not packages:
        raise BuildError(f"No Debian package was produced for {debian_version}.")

    primary_seen = False
    for package in packages:
        package_arch = capture(["dpkg-deb", "-f", str(package), "Architecture"])
        package_name = capture(["dpkg-deb", "-f", str(package), "Package"])
        package_version = capture(["dpkg-deb", "-f", str(package), "Version"])
        if package_version != debian_version:
            raise BuildError(
                f"Unexpected Debian version for {package_name}: {package_version}."
            )
        if package_arch not in {"all", expected_arch}:
            raise BuildError(
                f"Unexpected Debian architecture for {package_name}: {package_arch}."
            )
        if package_name == "onboard" and package_arch == expected_arch:
            listing = capture(["dpkg-deb", "-c", str(package)])
            if "usr/bin/onboard" not in listing:
                raise BuildError(
                    "The primary Debian package is missing the onboard launcher."
                )
            primary_seen = True
        copy_file(package, output / package.name)
    if not primary_seen:
        raise BuildError(
            f"The primary onboard package was not produced for {expected_arch}."
        )

    for pattern in (
        f"onboard_{debian_version}_*.buildinfo",
        f"onboard_{debian_version}_*.changes",
    ):
        for metadata in sorted(ROOT.parent.glob(pattern)):
            copy_file(metadata, output / metadata.name)
    write_candidate_metadata(
        output, target_os="linux-debian", arch=arch, version=version
    )
    return output


def build_rpm_candidate(arch: str, version: str) -> Path:
    require_host("linux")
    expected_arch = {"x64": "x86_64", "arm64": "aarch64"}[arch]
    for tool in ("rpm", "rpmbuild"):
        require_tool(tool)
    actual_arch = capture(["rpm", "--eval", "%{_arch}"])
    if actual_arch != expected_arch:
        raise BuildError(
            f"Expected RPM architecture {expected_arch}, but the host is {actual_arch}."
        )

    output = ROOT / "release-out" / f"rpm-{arch}"
    topdir = ROOT / "rpm-build"
    clean_paths(ROOT / "build", ROOT / "dist", topdir, output)
    run([sys.executable, "-m", "build", "--sdist", "--no-isolation"])
    source_archive = ROOT / "dist" / f"onboard-{version}.tar.gz"
    require_file(source_archive)
    for directory in ("BUILD", "BUILDROOT", "RPMS", "SOURCES", "SPECS", "SRPMS"):
        (topdir / directory).mkdir(parents=True, exist_ok=True)
    copy_file(source_archive, topdir / "SOURCES" / source_archive.name)
    copy_file(ROOT / "packaging/fedora/onboard.spec", topdir / "SPECS/onboard.spec")
    run(
        [
            "rpmbuild",
            "-ba",
            "--define",
            f"_topdir {topdir}",
            str(topdir / "SPECS/onboard.spec"),
        ]
    )

    output.mkdir(parents=True)
    artifacts = sorted((topdir / "RPMS").glob("*/*.rpm")) + sorted(
        (topdir / "SRPMS").glob("*.src.rpm")
    )
    if not artifacts:
        raise BuildError("No RPM artifacts were produced.")
    primary_seen = False
    for artifact in artifacts:
        package_name = capture(["rpm", "-qp", "--qf", "%{NAME}", str(artifact)])
        package_version = capture(["rpm", "-qp", "--qf", "%{VERSION}", str(artifact)])
        package_arch = capture(["rpm", "-qp", "--qf", "%{ARCH}", str(artifact)])
        if package_version != version:
            raise BuildError(
                f"Unexpected RPM version for {package_name}: {package_version}."
            )
        if artifact.suffix != ".rpm":
            raise BuildError(f"Unexpected RPM artifact suffix: {artifact.name}.")
        if (
            not artifact.name.endswith(".src.rpm")
            and package_name == "onboard"
            and package_arch == expected_arch
        ):
            listing = capture(["rpm", "-qlp", str(artifact)])
            if "/usr/bin/onboard" not in listing and "usr/bin/onboard" not in listing:
                raise BuildError("The primary RPM is missing the onboard launcher.")
            primary_seen = True
        copy_file(artifact, output / artifact.name)
    if not primary_seen:
        raise BuildError(
            f"The primary onboard RPM was not produced for {expected_arch}."
        )
    write_candidate_metadata(output, target_os="linux-rpm", arch=arch, version=version)
    return output


def build_arch_candidate(arch: str, version: str) -> Path:
    require_host("linux")
    expected_arch = {"x64": "x86_64", "arm64": "aarch64"}[arch]
    if platform.machine().lower() != expected_arch:
        raise BuildError(
            f"Expected Arch architecture {expected_arch}, but the host is {platform.machine()}."
        )
    for tool in ("makepkg", "pacman", "bsdtar"):
        require_tool(tool)

    work = ROOT / "arch-build"
    output = ROOT / "release-out" / f"arch-{arch}"
    clean_paths(ROOT / "build", ROOT / "dist", work, output)
    run([sys.executable, "-m", "build", "--sdist", "--no-isolation"])
    source_archive = ROOT / "dist" / f"onboard-{version}.tar.gz"
    require_file(source_archive)
    work.mkdir(parents=True)
    copy_file(ROOT / "packaging/arch/PKGBUILD", work / "PKGBUILD")
    copy_file(source_archive, work / source_archive.name)

    if hasattr(os, "geteuid") and os.geteuid() == 0:
        subprocess.run(
            ["useradd", "--create-home", "--shell", "/bin/bash", "builder"],
            check=False,
        )
        run(["chown", "-R", "builder:builder", str(work)])
        run(
            [
                "runuser",
                "-u",
                "builder",
                "--",
                "makepkg",
                "--noconfirm",
                "--cleanbuild",
            ],
            cwd=work,
        )
    else:
        run(["makepkg", "--noconfirm", "--cleanbuild"], cwd=work)

    output.mkdir(parents=True)
    packages: list[Path] = []
    for suffix in ("*.pkg.tar.zst", "*.pkg.tar.xz", "*.pkg.tar.gz"):
        packages.extend(sorted(work.glob(suffix)))
    if not packages:
        raise BuildError("No Arch package was produced.")
    primary_seen = False
    for package in packages:
        info = capture(["pacman", "-Qip", str(package)])
        package_name = re.search(r"^Name\s*:\s*(.+)$", info, re.MULTILINE)
        package_arch = re.search(r"^Architecture\s*:\s*(.+)$", info, re.MULTILINE)
        if package_name and package_arch and package_name.group(1) == "onboard":
            if package_arch.group(1) != expected_arch:
                raise BuildError(
                    f"Unexpected Arch package architecture: {package_arch.group(1)}."
                )
            listing = capture(["bsdtar", "-tf", str(package)])
            if "usr/bin/onboard" not in listing.splitlines():
                raise BuildError(
                    "The primary Arch package is missing the onboard launcher."
                )
            primary_seen = True
        copy_file(package, output / package.name)
    if not primary_seen:
        raise BuildError(
            f"The primary onboard package was not produced for {expected_arch}."
        )
    write_candidate_metadata(output, target_os="linux-arch", arch=arch, version=version)
    return output


def build_flatpak_candidate(arch: str, version: str) -> Path:
    require_host("linux")
    require_architecture(arch)
    for tool in ("flatpak", "flatpak-builder"):
        require_tool(tool)
    build = ROOT / f"flatpak-build-{arch}"
    repository = ROOT / f"flatpak-repo-{arch}"
    output = ROOT / "release-out" / f"flatpak-{arch}"
    clean_paths(build, repository, output)
    output.mkdir(parents=True)
    run(
        [
            "flatpak",
            "remote-add",
            "--if-not-exists",
            "--user",
            "flathub",
            "https://dl.flathub.org/repo/flathub.flatpakrepo",
        ]
    )
    run(
        [
            "flatpak",
            "install",
            "--user",
            "--noninteractive",
            "-y",
            "flathub",
            "org.gnome.Platform//50",
            "org.gnome.Sdk//50",
            "org.freedesktop.Sdk.Extension.rust-stable//25.08",
        ]
    )
    run(
        [
            "flatpak-builder",
            "--force-clean",
            f"--repo={repository}",
            str(build),
            "packaging/flatpak/org.onboard.Onboard.yml",
        ]
    )
    diagnostics = capture(["flatpak", "build", str(build), "onboard", "--diagnose"])
    if '"schema"' not in diagnostics:
        raise BuildError(
            "Flatpak diagnostic output did not contain the expected schema."
        )
    bundle = output / f"onboard-{version}-{arch}.flatpak"
    run(
        ["flatpak", "build-bundle", str(repository), str(bundle), "org.onboard.Onboard"]
    )
    if not bundle.is_file() or bundle.stat().st_size == 0:
        raise BuildError("Flatpak bundle was not produced.")
    write_candidate_metadata(
        output, target_os="linux-flatpak", arch=arch, version=version
    )
    return output


def command_candidate(args: argparse.Namespace) -> None:
    version = resolved_version(args.version)
    builders: dict[str, Callable[[str, str], Path]] = {
        "linux": build_linux_candidate,
        "debian": build_debian_candidate,
        "rpm": build_rpm_candidate,
        "arch": build_arch_candidate,
        "flatpak": build_flatpak_candidate,
    }
    output = builders[args.target](args.arch, version)
    if not output.is_dir():
        raise BuildError(f"Candidate build did not create {output.relative_to(ROOT)}.")
    log(f"Verified {args.target} candidate written to {output.relative_to(ROOT)}.")


def cargo_commit() -> str:
    return capture(["git", "rev-parse", "HEAD"])


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def build_windows_preview(arch: str, version: str) -> None:
    require_host("windows")
    require_architecture(arch)
    require_tool("cargo")
    manifest = ROOT / "next/Cargo.toml"
    binary = ROOT / "next/target/release/onboard-next.exe"
    output_root = ROOT / "release-out/windows" / arch
    output = output_root / f"onboard-next-preview-{version}"
    clean_paths(output)
    run(["cargo", "test", "--manifest-path", str(manifest), "--workspace", "--locked"])
    run(
        [
            "cargo",
            "build",
            "--manifest-path",
            str(manifest),
            "--bin",
            "onboard-next",
            "--release",
            "--locked",
        ]
    )
    require_file(binary)
    output.mkdir(parents=True)
    copy_file(binary, output / "onboard-next.exe")
    diagnostics = capture([str(output / "onboard-next.exe"), "diagnose", "ar_SA"])
    if '"direction":"rtl"' not in diagnostics:
        raise BuildError("Arabic RTL diagnostic failed for the Windows preview binary.")
    write_json(
        output / "provenance.json",
        {
            "product": "onboard-next",
            "channel": "preview",
            "platform": "windows",
            "architecture": arch,
            "version": version,
            "commit": cargo_commit(),
            "signed": False,
            "installer": "inno-setup-preview",
            "installer_signed": False,
            "input_source": "read-only-tsf-pending",
            "notes": "Preview bridge build. Do not treat as a signed stable installer.",
        },
    )
    write_checksums(output)
    archive = output_root / f"onboard-next-preview-{version}-windows-{arch}.zip"
    archive.unlink(missing_ok=True)
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as bundle:
        for item in sorted(path for path in output.rglob("*") if path.is_file()):
            bundle.write(item, item.relative_to(output_root))
    archive.with_suffix(archive.suffix + ".sha256").write_text(
        sha256(archive) + "\n", encoding="ascii"
    )
    compiler = shutil.which("ISCC.exe") or shutil.which("ISCC")
    if not compiler:
        raise BuildError(
            "Inno Setup ISCC compiler is required for the Windows installer."
        )
    recipe = ROOT / "packaging/windows/onboard-next-preview.iss"
    require_file(recipe)
    installer = output_root / f"onboard-next-preview-{version}-windows-{arch}-setup.exe"
    installer.unlink(missing_ok=True)
    run(
        [
            compiler,
            f"/DAppVersion={version}",
            f"/DArchitecture={arch}",
            f"/DInputDir={output}",
            f"/DOutputDir={output_root}",
            str(recipe),
        ]
    )
    if not installer.is_file() or installer.stat().st_size == 0:
        raise BuildError("Inno Setup did not produce a non-empty installer EXE.")
    installer.with_suffix(installer.suffix + ".sha256").write_text(
        sha256(installer) + "\n", encoding="ascii"
    )


def build_macos_preview(arch: str, version: str) -> None:
    require_host("darwin")
    require_architecture(arch)
    require_tool("cargo")
    manifest = ROOT / "next/Cargo.toml"
    binary = ROOT / "next/target/release/onboard-next"
    output = ROOT / "release-out/macos" / arch
    app = output / "Onboard-next.app"
    contents = app / "Contents"
    executable_directory = contents / "MacOS"
    resources = contents / "Resources"
    clean_paths(app)
    run(["cargo", "test", "--manifest-path", str(manifest), "--workspace", "--locked"])
    run(
        [
            "cargo",
            "build",
            "--manifest-path",
            str(manifest),
            "--bin",
            "onboard-next",
            "--release",
            "--locked",
        ]
    )
    require_file(binary)
    executable_directory.mkdir(parents=True)
    resources.mkdir(parents=True)
    copy_file(binary, executable_directory / "onboard-next")
    (executable_directory / "onboard-next").chmod(0o755)
    with (contents / "Info.plist").open("wb") as plist:
        plistlib.dump(
            {
                "CFBundleDevelopmentRegion": "en",
                "CFBundleExecutable": "onboard-next",
                "CFBundleIdentifier": "org.onboard.OnboardNext",
                "CFBundleInfoDictionaryVersion": "6.0",
                "CFBundleName": "Onboard-next Preview",
                "CFBundlePackageType": "APPL",
                "CFBundleShortVersionString": version,
                "CFBundleVersion": version,
                "LSMinimumSystemVersion": "12.0",
            },
            plist,
        )
    run(["plutil", "-lint", str(contents / "Info.plist")])
    diagnostics = capture(
        [str(executable_directory / "onboard-next"), "diagnose", "ar_SA"]
    )
    if '"direction":"rtl"' not in diagnostics:
        raise BuildError("Arabic RTL diagnostic failed for the macOS preview binary.")
    write_json(
        resources / "provenance.json",
        {
            "product": "onboard-next",
            "channel": "preview",
            "platform": "macos",
            "architecture": arch,
            "version": version,
            "commit": cargo_commit(),
            "signed": False,
            "notarized": False,
            "input_source": "read-only-tis-pending",
            "notes": "Preview bridge build. Do not treat as a signed or notarized stable application.",
        },
    )
    output.mkdir(parents=True, exist_ok=True)
    archive = output / f"onboard-next-preview-{version}-macos-{arch}.zip"
    dmg = output / f"onboard-next-preview-{version}-macos-{arch}.dmg"
    clean_paths(archive, dmg)
    run(
        ["ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(app), str(archive)]
    )
    run(
        [
            "hdiutil",
            "create",
            "-volname",
            "Onboard-next Preview",
            "-srcfolder",
            str(app),
            "-ov",
            "-format",
            "UDZO",
            str(dmg),
        ]
    )
    write_checksums(output, recursive=True)


def command_preview(args: argparse.Namespace) -> None:
    version = args.version or "0.1.0"
    if args.platform == "windows":
        build_windows_preview(args.arch, version)
    else:
        build_macos_preview(args.arch, version)
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
    absent = [
        str(path.relative_to(ROOT)) for path in required_files if not path.is_file()
    ]
    if absent:
        raise BuildError("Required package assets are missing: " + ", ".join(absent))
    installer_recipe = ROOT / "packaging/windows/onboard-next-preview.iss"
    installer_markers = (
        "OutputBaseFilename=onboard-next-preview-",
        "PrivilegesRequired=lowest",
        "ArchitecturesAllowed=",
        r'Source: "{#InputDir}\{#AppExecutable}"',
    )
    installer_content = installer_recipe.read_text(encoding="utf-8")
    missing_installer = [
        marker for marker in installer_markers if marker not in installer_content
    ]
    if missing_installer:
        raise BuildError(
            "Windows installer recipe is missing: " + ", ".join(missing_installer)
        )
    log("Package recipe validation completed successfully.")


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        description="Unified host-native build, package, preview and validation interface for Onboard."
    )
    subparsers = root.add_subparsers(dest="command", required=True)

    doctor = subparsers.add_parser(
        "doctor", help="Report host capabilities and declared project version."
    )
    doctor.set_defaults(handler=command_doctor)

    portable = subparsers.add_parser(
        "portable", help="Build and verify portable Linux wheel and source artifacts."
    )
    portable.add_argument(
        "--prepare",
        action="store_true",
        help="Install host build prerequisites before building.",
    )
    portable.set_defaults(handler=command_portable)

    native = subparsers.add_parser(
        "native", help="Verify and build the native Rust bridge on the current host."
    )
    native.add_argument(
        "--check-only",
        action="store_true",
        help="Use cargo check for tests before the release build.",
    )
    native.set_defaults(handler=command_native)

    candidate = subparsers.add_parser(
        "candidate",
        help="Build a host-native candidate with the selected package recipe.",
    )
    candidate.add_argument(
        "target", choices=CANDIDATE_BACKENDS, help="Candidate artifact family."
    )
    candidate.add_argument(
        "--arch",
        choices=ARCHITECTURES,
        default=detected_architecture(),
        help="Native target architecture.",
    )
    candidate.add_argument(
        "--version", help="Optional exact version guard; defaults to pyproject.toml."
    )
    candidate.set_defaults(handler=command_candidate)

    preview = subparsers.add_parser(
        "preview", help="Build a host-native unsigned onboard-next preview."
    )
    preview.add_argument(
        "platform", choices=("windows", "macos"), help="Native preview platform."
    )
    preview.add_argument(
        "--arch",
        choices=ARCHITECTURES,
        default=detected_architecture(),
        help="Native target architecture.",
    )
    preview.add_argument("--version", help="Preview version; defaults to 0.1.0.")
    preview.set_defaults(handler=command_preview)

    recipes = subparsers.add_parser(
        "validate-recipes", help="Validate static package recipe contracts."
    )
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
        print(
            f"[onboard-build] command failed with exit code {error.returncode}.",
            file=sys.stderr,
        )
        return error.returncode or 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
