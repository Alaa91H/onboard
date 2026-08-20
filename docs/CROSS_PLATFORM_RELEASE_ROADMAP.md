# Onboard: cross-platform independent application and release roadmap

## Decision

Onboard will be developed as an **independent desktop application**. GNOME Shell,
KDE, and platform services are integrations around the application; they are not
the application itself. The recommended end state is a native Rust core plus a
GTK4 Rust user interface (`onboard-next`) and a small platform bridge selected
at runtime. The existing Python/GTK3 application (`onboard-classic`) remains the
stable Linux product during the transition, retaining the completed Arabic,
RTL, input-source, clipboard, layout, and quick-access work.

The current source cannot honestly be called a ready Windows or macOS product:
it has Linux-specific X11, AT-SPI, uinput, D-Bus, GTK3 packaging, and C/C++
extensions. Shipping an untested binary that merely starts would not meet the
release-quality requirement. The plan therefore produces release artifacts only
when the matching platform gate has passed.

## Why Rust for the core and bridges

Rust is used for the bounded, security-sensitive work: input-state handling,
keymap validation, native input bridges, structured error codes, platform
capability detection, and packaging-friendly shared libraries. The current
PyO3 module is the first compatibility bridge for the Linux application; it is
not yet an input injector.

The long-term UI also uses Rust/GTK4. It avoids splitting business rules between
Python and JavaScript, keeps native accessibility semantics, and lets all three
desktop targets use the same presentation layer. GTK applications can be
bundled for Windows and macOS, but each target must be built on its own native
operating system and architecture.[1] [2]

| Option | Result | Recommendation |
|---|---|---|
| Keep Python/GTK3 and add platform conditionals | Fastest short-term Linux work but extensive platform-specific packaging debt | Maintain only as `onboard-classic` during transition. |
| Rust core with Python/GTK3 indefinitely | Improves Linux input reliability but still inherits GTK3/Python distribution complexity on Windows and macOS | Transitional compatibility layer only. |
| **Rust core plus GTK4 Rust interface** | One strongly typed UI/core, native bridges per OS, portable release process | **Target architecture for `onboard-next`.** |
| Browser or Electron shell | Easy visual portability but unsuitable as the primary assistive on-screen keyboard and adds a large runtime | Do not use. |

## Product and repository layout

The migration is additive. No release deletes the classic application until the
next application has feature-parity and accessibility sign-off.

```text
onboard/
├── Onboard/                                  # onboard-classic: Python/GTK3 Linux application
├── native/
│   └── onboard-native/                       # Current PyO3 compatibility extension
├── next/                                     # onboard-next: new independent Rust application
│   ├── Cargo.toml                            # Workspace root
│   ├── crates/
│   │   ├── onboard-core/                     # Layout model, clipboard model, i18n keys, state
│   │   ├── onboard-bridge-api/               # Platform-neutral capability and error contract
│   │   ├── onboard-bridge-linux/             # X11, xkbcommon, uinput and compositor adapters
│   │   ├── onboard-bridge-windows/           # SendInput, TSF input source, system tray
│   │   ├── onboard-bridge-macos/             # CGEvent, TIS input source, status item
│   │   ├── onboard-gtk/                      # GTK4 UI, RTL direction, a11y, themes
│   │   └── onboard-release/                  # Version/provenance manifest utility
│   ├── resources/
│   │   ├── i18n/                             # Fluent or gettext source and Arabic glossary
│   │   ├── layouts/                          # Platform-neutral compact/full layouts
│   │   └── icons/
│   └── tests/                                # Contract, a11y, RTL, and screenshot tests
├── packaging/
│   ├── linux/                                # deb, rpm, Flatpak, AppImage manifests
│   ├── windows/                              # MSIX/NSIS assets and signing layout
│   └── macos/                                # .app, DMG, entitlements, notarization layout
├── ci/
│   ├── scripts/                              # Reproducible build, smoke, and checksum scripts
│   └── release-manifest.schema.json          # Artifact metadata contract
├── docs/
│   ├── CROSS_PLATFORM_RELEASE_ROADMAP.md     # This decision record
│   └── ARCHITECTURE_RUST_I18N.md              # Current Rust/i18n transition boundary
└── .github/workflows/
    ├── portable-build.yml                    # Classic Linux source and package verification
    ├── platform-native.yml                   # Native x64/ARM64 bridge tests
    └── release.yml                           # Tag-only signed artifact publishing
```

## Stable bridge API

The bridge API has no GTK, Python, D-Bus, or platform types. All error messages
are stable machine codes; the UI resolves them through the one Arabic-aware
translation catalog. Every adapter reports a capability record before any
privileged action.

```text
BridgeCapabilities {
  platform: Linux | Windows | MacOS,
  architecture: X64 | Arm64,
  input_injection: Available | PermissionRequired | Unsupported,
  input_source: Available | ReadOnly | Unsupported,
  tray: Available | Unsupported,
  visibility: Available | Unsupported,
  detail_code: string
}
```

| Platform | Native bridge | Consent and fallback behavior |
|---|---|---|
| Linux X11 | XKB and controlled uinput/AT-SPI path | Detect group/source; never enable uinput permission silently. |
| Linux Wayland | compositor-specific virtual-keyboard/input-method adapter | Explicitly report permission or protocol absence because compositors may reject untrusted clients.[3] |
| Windows | `SendInput` for synthetic key events and TSF for input-source integration | Check integrity level and input-language capability; show a localized actionable state if blocked.[4] |
| macOS | Quartz `CGEvent` for key events and Text Input Services for source selection | Require the user-granted accessibility/input-monitoring capability before enabling injection.[5] |

## Release matrix

Every completed artifact is native-built on the target OS and architecture.
Cross-compilation is accepted only for development checks, never as the only
release validation. GitHub provides hosted Linux x64/ARM64, Windows x64/ARM64,
and macOS Intel/ARM64 runner labels; ARM64 Windows is preview and is therefore
kept as an allowed-warning verification until it becomes generally available.[2]

| Target | Architecture | Initial artifact | Required gate before publishing |
|---|---:|---|---|
| Linux | x64 | `.deb`, RPM, Flatpak, AppImage, source, wheel | Source build, GTK smoke test in Xvfb, Rust tests, Arabic/RTL, package inspection. |
| Linux | ARM64 | `.deb`, RPM, Flatpak, AppImage, source, wheel | Native ARM64 runner, same test set, no qemu-only release. |
| Windows | x64 | portable folder, NSIS installer, then signed MSIX | GTK4 UI smoke test, `SendInput` contract tests, Arabic/RTL, installer verification. |
| Windows | ARM64 | portable folder, MSIX | Native ARM64 runner plus actual ARM64 test; may be preview until runner exits preview. |
| macOS | x64 | `.app`, DMG | GTK4 UI smoke test, Quartz permission-state tests, codesign and bundle inspection. |
| macOS | ARM64 | `.app`, universal DMG or ARM64 DMG | Native Apple Silicon runner, same tests, codesign and notarization. |

## Build and publication policy

A pull request runs source and unit checks; it never publishes release assets.
A protected version tag starts the release matrix. Each artifact includes a
version, commit SHA, target triple, build time, SHA-256 checksum, SBOM, and
provenance record. The release job aggregates artifacts only if every required
gate succeeds; it never replaces a prior release asset.

The first public cross-platform preview is **unsigned and clearly labelled
Preview** until the repository has Windows Authenticode and Apple Developer
signing/notarization credentials. Without those user-owned credentials, it is
not technically or legally possible to issue a trustworthy signed Windows
installer or a notarized macOS application. The workflow must fail closed when
the secrets are absent on a stable-release tag.

## Staged implementation

| Milestone | Scope | Exit criterion |
|---|---|---|
| M0 — Repair and stabilize | PyO3 3.14 support, Linux x64/ARM64 CI, checksums, reproducible source build | Ubuntu, Fedora, and ARM64 Linux builds pass. |
| M1 — Formal bridge contract | Extract platform-neutral Rust API and Linux adapter behind runtime capabilities | No Linux behavior regression; fallback and permission tests pass. |
| M2 — `onboard-next` shell | GTK4 Rust compact keyboard, saved geometry, Arabic RTL, clipboard, emoji, local layouts | Accessible desktop app runs independently on Linux x64/ARM64. |
| M3 — Windows | GTK4 bundle, `SendInput` and TSF adapters, tray, NSIS/MSIX packaging | Native Windows x64 installer test passes. |
| M4 — macOS | GTK4 app bundle, Quartz/TIS adapter, status item, code-signing pipeline | Native macOS x64/ARM64 app bundle tests pass. |
| M5 — Release hardening | SBOM, checksums, signing, notarization, release notes, update strategy | Tagged builds generate verified user-installable artifacts. |

## Release-quality definition

A file is called **ready** only after all of the following are true for that
specific target:

1. It is compiled natively for the declared OS and architecture.
2. Automated Rust, UI, Arabic catalog, RTL, and package-content tests pass.
3. The application opens and closes in a target-native smoke test.
4. The bridge reports capability or permission status rather than failing
   silently.
5. The file checksum, commit SHA, and dependency manifest are attached.
6. Stable releases are signed; macOS stable releases are also notarized.

## References

[1]: https://pygobject.gnome.org/guide/deploy.html "PyGObject deployment guidance"
[2]: https://docs.github.com/en/actions/reference/runners/github-hosted-runners "GitHub-hosted runner architectures"
[3]: https://wayland.app/protocols/virtual-keyboard-unstable-v1 "Wayland virtual-keyboard protocol"
[4]: https://learn.microsoft.com/en-us/windows/win32/api/winuser/nf-winuser-sendinput "Microsoft SendInput"
[5]: https://developer.apple.com/documentation/coregraphics/quartz-event-services "Apple Quartz Event Services"
[6]: https://pyinstaller.org/en/stable/operating-mode.html "PyInstaller target-specific distribution"
