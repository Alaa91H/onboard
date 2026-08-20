# Onboard product-quality roadmap

## Product promise

Onboard is an **independent on-screen keyboard application**. It must remain
useful when no desktop-shell extension is installed, and it must report a clear
capability state whenever a platform security model prevents a privileged
operation. GNOME Shell, KDE, and future platform bridges are optional
integrations around the application, never prerequisites for opening a keyboard,
using Arabic, pasting from history, or selecting a saved layout.

The product target is a responsive mouse-first virtual keyboard for laptops as
well as touch devices. A user can invoke it quickly, move and resize it, reopen
it at the saved location, type in Arabic or English, inspect the active source,
use clipboard history and emoji, and recover from unsupported desktop features
without silent failure.

## Release channels and eligibility

| Channel | Intended users | Artifact rule | Publishing rule |
|---|---|---|---|
| Development | contributors | CI artifacts | every relevant push; never announced as a release |
| Preview | early testers | target-native, checksum-verified candidate | manually dispatched; clearly labelled Preview |
| Stable | general users | signed and target-native installer/package | protected tag; all required quality gates succeed |
| Long-term support | distributions | source, package recipes, security fixes | only after a stable branch is maintained |

A platform is **not** presented as supported merely because Rust compiles there.
It becomes release-eligible only when the complete independent application and
its platform bridge pass the gates in `CROSS_PLATFORM_RELEASE_ROADMAP.md`.

## Feature priorities

| Priority | Product area | Deliverable | Completion evidence |
|---|---|---|---|
| P0 | Independent invocation | status indicator, desktop action, command, saved geometry, single-instance behavior | regression and session tests |
| P0 | Real input source | X11 XKB, KDE D-Bus, GNOME Wayland bridge, clear readonly fallback | backend contract tests on supported sessions |
| P0 | Arabic first-class UX | complete Arabic catalog, six plural forms, RTL, consistent terminology | catalog, RTL, and UI smoke tests |
| P0 | Keyboard reliability | no lost keyboard events, robust focus behavior, deterministic keymap validation | native/Python contract tests |
| P1 | Compact productivity | Windows-Compact profile, clipboard history, emoji selector, recent-source menu | layout and menu regression tests |
| P1 | Accessibility | keyboard navigation, accessible labels, high contrast, predictable focus | AT-SPI and visual smoke tests |
| P1 | Privacy controls | clear clipboard history, bounded retention, no background network access | configuration and retention tests |
| P1 | Diagnostics | capability report, backend status, version/build manifest, exportable non-sensitive log | deterministic diagnostics test |
| P2 | `onboard-next` | Rust core plus GTK4 application shell, feature parity with classic | native Linux x64/ARM64 UI and a11y gate |
| P2 | Windows/macOS | native adapters and installers after `onboard-next` feature parity | target-native smoke, permission, installer and signing gates |

## Engineering rules

The existing `onboard-classic` code remains the production Linux path while
`onboard-next` is built incrementally. No rewrite removes a working feature
without a tested replacement. Rust owns tightly bounded native validation and
platform adapters; it returns stable capability/error codes. Presentation,
translations, and user-facing messages remain in a single catalog layer so an
error does not become English merely because it came from a native bridge.

Every behavior that changes input, clipboard, geometry, visibility, or locale
requires a deterministic regression test. Every desktop integration must be
optional, capability-gated, and fail closed. Every package must include the
Arabic catalog, Rust metadata, a source revision, and a checksum manifest.

## Milestones

| Milestone | Scope | Acceptance condition |
|---|---|---|
| Q1 — Stable Linux foundation | complete current P0 flows, native capability report, tests, source/wheel portability | Ubuntu and Fedora on x64/ARM64 plus Arch/Flatpak checks pass remotely |
| Q2 — Daily-driver refinement | clipboard/privacy controls, accessibility labels, compact-layout polish, diagnostics | P0/P1 regression suite and manual mouse-first acceptance checklist pass |
| Q3 — Native core transition | Rust bridge contract and GTK4 `onboard-next` core shell on Linux | independent GTK4 app passes Arabic/RTL/a11y and input-source fallback gates |
| Q4 — Desktop expansion | Windows and macOS adapters, packaging, signing/notarization setup | target-native installers pass on x64 and ARM64 with explicit permission states |
| Q5 — Stable release | release notes, SBOM, checksums, signatures, upgrade/rollback guidance | protected tag passes every mandatory stable gate |

## Non-negotiable stable-release gates

1. The artifact is built natively for its declared operating system and CPU
   architecture.
2. Source, Rust, Python, Arabic catalog, RTL, and package-content tests pass.
3. A smoke test opens and closes the application without a shell extension.
4. Input source and injection report their actual capability/permission state.
5. The artifact has a version, commit SHA, checksum manifest, and SBOM.
6. Stable Windows releases are Authenticode-signed; stable macOS releases are
   codesigned and notarized. Missing signing credentials fail a stable release
   rather than producing an untrusted installer.
