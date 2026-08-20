# Building and Desktop Compatibility

**Onboard** now exposes a standard PEP 517 build interface in addition to the
native Debian packaging. The common build path no longer requires
`python3-distutils-extra`; it compiles the C/C++ extensions, gettext catalogs,
and desktop entries using `setuptools`, `gettext`, and `intltool`.

> Native desktop support is determined by the display protocol and compositor
> capabilities, not by the Linux distribution name. In particular, Wayland does
> not require every compositor to provide a virtual-keyboard or layer-shell
> interface. [4]

## Supported distribution build targets

| Distribution family | Primary artifact | Maintained source entry point | Validation level |
|---|---|---|---|
| Debian and Ubuntu | `.deb` | `debian/` and `build_debs.sh` | Native package path |
| Fedora and RHEL derivatives | RPM | `packaging/fedora/onboard.spec` | PEP 517 build and RPM recipe |
| openSUSE | RPM | `packaging/fedora/onboard.spec`, adapted by the distribution maintainer | PEP 517 build and RPM recipe |
| Arch and derivatives | pacman package | `packaging/arch/PKGBUILD` | PEP 517 build and recipe syntax |
| Any Flatpak-enabled desktop | Flatpak preview | `packaging/flatpak/org.onboard.Onboard.yml` | UI sandbox build path |
| Other Linux distributions | Source / wheel | `pyproject.toml` and `setup.py` | Standard source build |

Fedora packaging should use the current Python build macros and a direct
`python3-devel` build dependency, rather than the deprecated
`setup.py install` workflow. [1] Arch packaging should keep direct run-time,
build-time, and test dependencies explicit in `PKGBUILD`. [2] Flatpak manifests
must declare the runtime, SDK, command, sources, and only the sandbox permissions
that are needed. [3]

## Preparing a native build environment

Run the repository helper from a clean source checkout. It detects `apt`, `dnf`,
`pacman`, or `zypper` and installs the matching compiler, GTK, X11, Wayland,
gettext, and Python development dependencies.

```bash
./tools/prepare-build-env.sh --with-tests
python3 setup.py build
python3 -m build --no-isolation
```

The build emits a source archive and an architecture-specific wheel in `dist/`.
The `setup.py build` command also creates development-only links to the native
extensions so the test suite can import them from the source tree. These links
must not be committed.

The build also compiles the optional `Onboard.onboard_native` Rust extension.
In this release it performs bounded keymap and event validation only; the
established virtkey/uinput and AT-SPI input paths remain the production
transport. Rust and Cargo are therefore build dependencies, never an additional
runtime service. A diagnostic source build can intentionally skip it while
retaining the safe Python reference implementation:

```bash
ONBOARD_DISABLE_RUST=1 python3 setup.py build
ONBOARD_NATIVE_INPUT=fallback onboard
```

See [the Rust and i18n architecture record](docs/ARCHITECTURE_RUST_I18N.md) for
the package layout, API boundary, and the controlled path to a future native
transport.

## Building a distribution package

| Target | Command outline | Result |
|---|---|---|
| Debian or Ubuntu | `./build_debs.sh` | Repository-ready `.deb` packages in `build/debs/` |
| Fedora / RHEL | Put the signed release archive beside `packaging/fedora/onboard.spec`, then run `rpmbuild -ba packaging/fedora/onboard.spec` | RPMs and source RPM |
| Arch | Copy the release archive beside `packaging/arch/PKGBUILD`, replace `SKIP` with its BLAKE2 checksum, then run `makepkg -f` | `.pkg.tar.zst` package |
| Flatpak | `flatpak-builder --user --install build-flatpak packaging/flatpak/org.onboard.Onboard.yml` | Sandboxed preview build |

The RPM and Arch files are **release templates**: a distribution maintainer must
set the final release source URL, checksum, and any policy-specific subpackages.
The uinput rule is deliberately shipped as a reviewable data file rather than
being silently enabled, because granting virtual-input access is a local security
policy decision.

## Desktop and window-manager capability matrix

| Session / compositor family | Floating & saved position | System language switch | Quick access | Recommended backend | Status |
|---|---|---|---|---|---|
| X11 under GNOME, KDE, Xfce, MATE, Cinnamon, i3, Openbox, etc. | Yes | XKB | StatusNotifier/AppIndicator or legacy tray; desktop action fallback | `auto` / X11 | Core support |
| KDE Plasma Wayland | Yes, through a KWin rule | KDE D-Bus | StatusNotifier/AppIndicator; desktop action fallback | `auto` | Enhanced support |
| GNOME Wayland | Yes, with the bundled GNOME Shell extension enabled | Extension D-Bus bridge | Permanent Onboard button in the right-hand Shell status area | `auto` | Enhanced support |
| sway, Hyprland, Wayfire, river, labwc, niri, COSMIC and similar Wayland compositors | Layer-shell placement where offered; compositor-controlled dragging is not portable | No portable system API | Panel indicator when the panel implements StatusNotifier; desktop action otherwise | `auto` or `x11` | Capability-limited |
| Other Wayland compositors | Depends on the compositor | No assumed API | Desktop action and `onboard-toggle` | `x11` where XWayland exists | Safe fallback |

The launcher reports the selected window and input-source strategies at startup.
It also accepts an explicit override when a compositor has partial or unusual
Wayland support:

```bash
ONBOARD_BACKEND=auto onboard       # default capability detection
ONBOARD_BACKEND=wayland onboard    # force native Wayland attempt
ONBOARD_BACKEND=x11 onboard        # force XWayland/X11 compatibility path
```

A forced native Wayland path is appropriate only when the compositor is known to
provide the needed protocols. A forced X11 path needs XWayland. The project does
not label a language change as successful until the desktop backend confirms the
active source.

## Persistent quick access

Onboard enables its status icon by default and a primary click now toggles the
keyboard immediately. KDE and panels with StatusNotifier/AppIndicator support
show that icon alongside their other system indicators. GNOME's default shell
has no legacy tray, so the bundled extension adds a permanent keyboard button to
the same right-hand status area used by system indicators. GNOME Shell controls
the exact ordering of built-in items such as the language source; the extension
therefore does not replace or monkey-patch the language item.

Every installation also provides a desktop-entry action named **Show or hide
Onboard** and an `onboard-toggle` command. Bind that command to the desktop's
custom shortcut facility when the panel does not expose a status-indicator
protocol:

```bash
onboard-toggle
```

The command toggles the running instance over session D-Bus and starts Onboard
only when no instance is available, so it does not create duplicate keyboards.

## Arabic localization

The standalone application ships a complete Arabic gettext catalog for the
keyboard menus, preferences, desktop entries, clipboard states, input-source
messages, emoji descriptions, and diagnostic dialogs. The catalog is compiled
into `share/locale/ar/LC_MESSAGES/onboard.mo` by every supported package path.
A desktop session configured for Arabic selects it automatically; maintainers
can verify it from a shell without changing the whole session:

```bash
LANG=ar_SA.UTF-8 LANGUAGE=ar GTK_TEXT_DIR=rtl onboard
LANG=ar_SA.UTF-8 LANGUAGE=ar GTK_TEXT_DIR=rtl onboard-settings
```

When adding a new user-visible Python string, wrap it in `_()` and include its
source file in `po/POTFILES.in`. Then refresh the catalog and validate it before
release:

```bash
python3 setup.py build_i18n
msgmerge --update --backup=none po/ar.po po/onboard.pot
python3 i18n/scripts/check_catalog.py po/ar.po --language ar --require-complete
msgfmt --check --statistics po/ar.po
```

## Validation and release gate

The `Portable build` workflow validates the generic source build on Ubuntu and
Fedora, runs the focused input-source, clipboard, layout, and capability tests,
and checks the Arch and Flatpak templates. It also runs the Rust crate tests,
the Rust/Python fallback contract, the RTL selector test, and the complete
Arabic gettext catalog gate. Before a stable release, additionally perform
manual smoke tests in a real Arabic KDE Wayland and GNOME Wayland session; a
headless X11 test cannot validate compositor-owned D-Bus policies, desktop
extensions, or visual RTL clipping.

## References

[1]: https://docs.fedoraproject.org/en-US/packaging-guidelines/Python/ "Fedora Python Packaging Guidelines"
[2]: https://wiki.archlinux.org/title/PKGBUILD "ArchWiki: PKGBUILD"
[3]: https://docs.flatpak.org/en/latest/manifests.html "Flatpak documentation: Manifests"
[4]: https://wayland.app/protocols/virtual-keyboard-unstable-v1 "Wayland virtual-keyboard protocol"
