# Onboard native Rust, i18n, and RTL architecture

## Purpose and current safety boundary

Onboard remains an independent Python/GTK application. The Rust crate introduced
in this branch is an **optional validation-only native component**: it validates
keymaps and records key state, but it does not open `/dev/uinput`, create a
Wayland virtual keyboard, or emit a keystroke. The existing virtkey/uinput and
AT-SPI paths remain the production behavior until the native transport passes
real-session parity tests.

> Rust is a narrow capability layer, not a replacement UI framework. Python
> owns GTK, GObject lifecycle, D-Bus, configuration, gettext, and the fallback
> policy. GNOME Shell integration remains a small optional JavaScript bridge.

Wayland virtual-keyboard permission is granted by the compositor, not by the
language of a client. A compositor may reject an untrusted request, so a future
Rust transport is always capability-gated and never replaces the safe fallback
merely because the extension is installed.[1]

## Repository structure

```text
onboard/
├── Onboard/                              # Python/GTK application boundary
│   ├── I18n.py                            # Locale precedence and GTK RTL/LTR direction
│   ├── NativeInput.py                     # Stable Python contract and safe fallback
│   ├── InputSources.py                    # X11/KDE/GNOME source-selection policy
│   ├── WaylandUtils.py                    # Session capability detection
│   ├── Keyboard.py                        # Existing production key-synthesis path
│   └── test/
│       ├── test_NativeInput.py             # Rust/fallback contract tests
│       ├── test_RTL.py                     # Headless locale and GTK-direction tests
│       └── test_ArabicLocalization.py      # Runtime catalog and desktop-entry tests
├── native/
│   └── onboard-native/                    # Isolated Rust crate
│       ├── Cargo.toml                      # PyO3 cdylib and reproducible crate metadata
│       ├── Cargo.lock                      # Locked dependency graph
│       ├── .cargo/config.toml              # Uses the checked-in vendor directory
│       ├── src/
│       │   └── lib.rs                       # PyO3 module and bounded input state machine
│       └── vendor/                          # Offline sources for isolated/Flatpak builds
├── i18n/
│   ├── README.md                           # gettext and RTL contributor workflow
│   ├── glossary/ar.md                      # Approved Arabic UI terminology
│   └── scripts/check_catalog.py            # CI catalog quality gate
├── po/
│   ├── POTFILES.in                         # All extractable source/UI/desktop inputs
│   ├── onboard.pot                         # Generated gettext template
│   └── ar.po                               # Reviewed Arabic catalog and six plural forms
├── data/
│   ├── *.desktop.in                        # Localized launchers and actions
│   └── gnome-extension/                    # Optional GNOME Shell bridge
├── packaging/
│   ├── arch/PKGBUILD
│   ├── fedora/onboard.spec
│   └── flatpak/org.onboard.Onboard.yml
├── tools/prepare-build-env.sh              # Cross-distribution build prerequisites
├── docs/ARCHITECTURE_RUST_I18N.md          # This design record
├── setup.py                                # Builds C/C++ extensions, gettext, and the Rust cdylib
└── pyproject.toml                          # PEP 517 entry point
```

## Native input contract

The Python contract has a deliberately small API. No GTK object, GObject,
Python pointer, D-Bus proxy, or callback passes through it.

| Operation | Python caller sends | Native layer returns | Ownership |
|---|---|---|---|
| `open(device_path)` | a logical device path | success or stable error code | Native layer owns only its local state. |
| `install_keymap(bytes)` | UTF-8 keymap bytes | success or `invalid-keymap:*` | Native layer validates and copies bytes. |
| `key(code, pressed, time)` | integer event data | success or `invalid-keycode:*` | Native layer records bounded state. |
| `modifiers(...)` | four integer masks | no UI text | Native layer records state. |
| `close()` | no value | no value | Native layer clears volatile state. |

`Onboard.NativeInput` selects Rust in `auto` mode when the packaged extension
exists. It returns the Python validation reference implementation when it does
not. `ONBOARD_NATIVE_INPUT=native` makes absence explicit for diagnostics, and
`ONBOARD_NATIVE_INPUT=fallback` forces the Python reference implementation.

The next native milestone may implement a separately authorized uinput or
Wayland transport, but it must preserve this contract and pass the same tests.
A native error is a machine-readable code such as `permission-denied` or
`protocol-unavailable`; Python maps it to gettext text. This design ensures
that Arabic and every other language have one translation catalog.

## Build and packaging model

`setup.py build` invokes Cargo and copies the resulting PyO3 extension to the
platform-tagged `Onboard/onboard_native*.so` path inside `build_lib`. The normal
PEP 517 command remains unchanged:

```bash
python3 -m build --no-isolation
```

The Rust crate is vendored, so isolated package and Flatpak builds need not
download crates during compilation. The Debian/Fedora/Arch/openSUSE helper
installs Cargo and Rust alongside the pre-existing C/C++ and GTK requirements.
The Flatpak manifest enables the Rust SDK extension during build only; it does
not alter runtime sandbox permissions.

PyO3 supports building Python extension modules and recognizes both `maturin`
and `setuptools-rust` packaging approaches.[2] This repository uses a focused
`setup.py` command because Onboard already has custom C/C++ extension and
gettext build steps; retaining one PEP 517 entry point reduces release risk.

## i18n and RTL model

All user-facing strings originate in `po/onboard.pot`, synchronize into
`po/ar.po`, and compile into `onboard.mo`. GNU gettext's standard workflow is
source → POT → PO → MO, and supports contextual and plural translations.[3]

`Onboard.I18n` resolves locale variables in gettext order: `LANGUAGE`,
`LC_ALL`, `LC_MESSAGES`, then `LANG`. If the selected language is Arabic or
another recognized RTL language, it sets `Gtk.Widget`'s default direction to
RTL **before** the keyboard or preferences GtkBuilder objects are created. It
sets LTR otherwise. Text direction is separate from keyboard key order: Arabic
interface text mirrors as GTK intends, while key layouts continue to control
their own physical/linguistic geometry.

The CI catalog gate verifies syntax, gettext format rules, zero fuzzy entries,
zero active untranslated entries for Arabic, the `Language: ar` header, and
Arabic's six plural forms. The release gate also includes a real Arabic session
smoke test because clipping and mnemonic conflicts cannot be proved by a
headless test alone.

## Verification layers

| Layer | Verification |
|---|---|
| Rust crate | `cargo test --locked` validates keymap and keycode bounds. |
| Python boundary | `test_NativeInput` proves equivalent Rust/fallback behavior and explicit fallback selection. |
| RTL | `test_RTL` checks locale precedence and calls the GTK direction setter through a headless fake. |
| Arabic catalog | `check_catalog.py` plus `msgfmt --check` enforces complete, non-fuzzy Arabic gettext data. |
| Package contents | PEP 517 checks ensure that the extension and `ar/LC_MESSAGES/onboard.mo` are included. |
| Remote builds | Ubuntu and Fedora compile C/C++, Rust, gettext, and Python tests; Arch/Flatpak templates are linted. |

## References

[1]: https://wayland.app/protocols/virtual-keyboard-unstable-v1 "Wayland virtual-keyboard protocol"
[2]: https://pyo3.rs/main/building-and-distribution "PyO3: Building and distribution"
[3]: https://docs.weblate.org/en/weblate-5.15.1/devel/gettext.html "Weblate: Translating software using GNU gettext"
