# Running Onboard on Wayland

Onboard's primary target has historically been X11/Xorg. Initial
phase of Wayland support adds an unstable experience on Wayland.

- KDE Plasma - ✅ should work well.
- GNOME Mutter - ✅ should work well via a bundled GNOME Shell extension or an automatic XWayland fallback.
- Pop_OS (Cosmic) - typing works but not possible to move the window (XWayland fallback via `GDK_BACKEND=x11` does not seem to work, impossible to type). 
- Sway, Hyprland, ... - typing works, anchored to the bottom of the screen. 

## Limitations / not yet implemented / TODO

- Move/resize issues if not on KDE or GNOME.
- Docking to screen edge may not work correctly (in KDE and GNOME, except XWayland). 
- Mouse actions (right/middle click) not working.
- Text snippets may get inserted incorrectly if using multiple layouts.
  If the snippet characters do not exist the current layout, they may get inserted incorrectly.
  To avoid that, trying to insert via AT-SPI when possible, so it should work correctly in the apps that support it, such as the KDE apps using the modern Qt. 
- On Wayland compositors other than KDE Plasma and GNOME Shell, there is no stable, common
  desktop API for an external application to control the active input source. Onboard disables
  its source-switch button there instead of pretending that a language has changed.
- Try implementing the `virtual-keyboard-v1` Wayland backend — would remove the `/dev/uinput` permission
  requirement on the compositors that support it.
- Negotiate client-side decoration via the `xdg-decoration` protocol so the
  "Show window decoration" preference works natively on KDE (currently
  needs a manual KWin `noborder` window rule as a workaround).

## Setup

### 1. Install runtime dependencies

Depending on your distro and compositor, you may need to install these dependencies
(in addition to the ones in [README.md](README.md)). 

Debian/Ubuntu/Kubuntu:

```sh
sudo apt install gir1.2-gtklayershell-0.1 gir1.2-atspi-2.0
```

Arch:

```sh
sudo pacman -S gtk-layer-shell at-spi2-core
```

Fedora:

```sh
sudo dnf install gtk-layer-shell at-spi2-core
```

### 2. Enable `/dev/uinput` for your user

There is an udev rule at [data/72-onboard-uinput.rules](data/72-onboard-uinput.rules). The Debian
package or `sudo python3 setup.py install` put it into `/lib/udev/rules.d/` or `/usr/local/lib/udev/rules.d/` automatically.

Or install manually if running from source or something failed:

```sh
sudo cp data/72-onboard-uinput.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules
sudo udevadm trigger /dev/uinput
```

That's it, `input` group membership or re-login is not required.

You can verify the ACL is applied while Onboard is running:

```sh
getfacl /dev/uinput | grep "user:$USER"     # should show 'rw-'
# Once Onboard is started:
getfacl $(ls -t /dev/input/event* | head -1) | grep "user:$USER"
```

Both should report `rw-` for your user.

### 3. Run

As usual, run

```sh
onboard
```

(or click the installed app icon etc.)

Onboard auto-selects the right backend. On compositors without
layer-shell or on GNOME without the extension it sets `GDK_BACKEND=x11` automatically,
you don't need to set it manually. To force a backend (e.g. for
testing), set `GDK_BACKEND` before launch (e.g. `GDK_BACKEND=x11 onboard` or `GDK_BACKEND=wayland onboard`).

If you run

```sh
onboard --debug=info
```

The startup log will say something like this (on KDE):

```
INFO: Display server: Wayland (KDE)
INFO: KWin window rule 'onboard' installed at ~/.config/kwinrulesrc
INFO: Using KWin window rule for keyboard window (drag + resize stay available)
INFO: Using key-synth 'KeySynthEnum.UINPUT'
```

If the key-synth line says `ATSPI` instead of `UINPUT`, uinput failed —
the udev rule isn't installed (or hasn't been reloaded). See step 2.

### 4. Switch the real input source

The **input-source** key in the standard `Compact` and `Full Keyboard`
layouts is the right Super-key position. A tap requests the next configured system source; a
long press opens a list of the configured sources. This key is deliberately
separate from the word-prediction **language** key. The input-source key
changes the layout that applications actually receive, while the language
key only changes Onboard's prediction model.

Onboard updates its label only after the desktop session confirms the active
source. It does not optimistically display Arabic or English before a switch
has succeeded.

| Session | Switching backend | Confirmation |
|---|---|---|
| X11/Xorg | Existing XKB/Virtkey group control | Active XKB group read after lock |
| KDE Plasma Wayland | `org.kde.KeyboardLayouts` session D-Bus | `layoutChanged` or `layoutListChanged` |
| GNOME Wayland | Constrained interface from the bundled Onboard Shell extension | `current-source-changed` from GNOME Shell |
| Other Wayland compositors | No unsafe fallback | The source key is disabled with an explanatory tooltip |

For a native GNOME Wayland session, update or reinstall the bundled extension
and restart the Shell session (log out and in on Wayland). The extension
exports only list, get, activate, and next-source operations under
`/org/onboard/InputSources`; it never exposes a general JavaScript execution
interface.

To diagnose source switching:

```sh
onboard --debug=info 2>&1 | grep -i 'input source'
```

A successful confirmation is logged as `Input source confirmed: …`.

## Implementation details

### KDE Plasma

Onboard installs a window rule into `~/.config/kwinrulesrc` keyed on the
Wayland `app_id="onboard"`. The rule sets `acceptfocus=false` so KWin
never gives the keyboard window keyboard focus, even on click. The window
itself remains a regular GTK toplevel — so dragging it by its frame works,
resizing works.

**Window decoration:** KWin draws its own server-side decoration for
regular `xdg-shell` toplevels and ignores the GTK-side
`window_decoration` preference (`gtk_window_set_decorated()`) unless the
app explicitly negotiates client-side decoration via the
`xdg-decoration` protocol, which Onboard does not do yet. So unchecking
"Show window decoration" in Onboard's preferences has no visible effect
under KDE. If you want a borderless keyboard window on KDE, add
`noborder=true` / `noborderrule=2` to the window rule below (see
Troubleshooting).

### GNOME Mutter (native Wayland via bundled Shell extension)

Onboard ships a GNOME Shell extension (`onboard@onboard.local`).
It watches for windows with `wm_class="Onboard"`,
calls `Meta.Window.make_above()` on them, and reverts keyboard
focus to the previously focused window when Onboard accidentally
receives it. It also exposes a deliberately narrow D-Bus bridge for
Onboard's input-source key. The bridge gets its state from GNOME Shell's
`InputSourceManager`, activates only configured sources, and emits a
confirmation signal after Shell changes the current source.

The extension is auto-installed on first launch into
`~/.local/share/gnome-shell/extensions/onboard@onboard.local/` and
enabled via `gnome-extensions enable`. Onboard injects the running
gnome-shell major version into `metadata.json` so the extension
doesn't auto-disable after each GNOME bump.

After the installation, you may need to **reboot or log out** because extensions do not start until the next session.
Until the extension is active and the world should automatically switch to XWayland.

After installation you should see, in `onboard --debug=info`:

```
INFO: Display server: Wayland (GNOME)
INFO: gtk-layer-shell available: False
INFO: Onboard GNOME Shell extension 'onboard@onboard.local' installed and enabled at ~/.local/share/gnome-shell/extensions/onboard@onboard.local
INFO: Using GNOME Shell extension for keyboard window (drag + resize stay available)
INFO: Using key-synth 'KeySynthEnum.UINPUT'
```

The keyboard is a regular GTK toplevel, so drag + resize
work normally. Docking is unavailable on the native Wayland — Mutter
has no mechanism for a regular toplevel to reserve screen space. If you need docking on GNOME, opt out of the
extension and the auto-XWayland fallback (below) will provide
`_NET_WM_STRUT_PARTIAL`-based docking.

To opt out of the extension, simply disable it:

```sh
gnome-extensions disable onboard@onboard.local
```

Onboard will **not** re-enable the extension on subsequent launches if you have explicitly disabled
it (via `gnome-extensions disable` or the GNOME Extensions app).

Onboard will then auto-route through XWayland on subsequent launches.

### GNOME Mutter (XWayland auto-fallback)

When the bundled GNOME Shell extension is not installed or is
disabled, Onboard's launcher sets `GDK_BACKEND=x11` before any
GTK code loads. Onboard then comes up as an XWayland client and uses
the X11 hints Mutter honors (`set_keep_above`, `set_accept_focus(False)`, ...)
and overall everything seems to work fine on this compositor.
Key injection is still done via `uinput`.

You will see the routing decision in `onboard --debug=info` output:

```
INFO: Routed through XWayland: compositor lacks both wlr-layer-shell
       and a KWin-rule equivalent. X11 hints (above, no-focus-steal,
       strut) work fine.
INFO: Display server: X11
```

To override the auto-selection (e.g. force native Wayland for
testing), export `GDK_BACKEND` yourself before launch:

```sh
GDK_BACKEND=wayland onboard
```

### Other compositors with layer-shell

On Pop_OS, sway, Hyprland and other compositors that implement
`zwlr_layer_shell_v1`, Onboard falls back to `gtk-layer-shell`. The
keyboard becomes a layer surface anchored to the bottom of the screen,
full width. Drag and resize through the compositor are unavailable,
layer-shell surfaces aren't toplevel windows. In the future
Onboard should add its own margin-based drag for these compositors.

## Troubleshooting

### Nothing is typed

Usually an uinput / udev rule issue. Quick diagnostic:

```sh
onboard --debug=DEBUG 2>&1 | \
    grep -iE 'wayland:|key-synth|uinput|kwin'
```

If you see `Wayland: Found /dev/input/eventN but it is not readable`, the
udev rule isn't applied. Re-run step 2 of the setup.

Also check `modinfo uinput`.

### Onboard cannot type and steals focus on KDE

The KWin rule may not have been picked up. Verify:

```sh
grep -A 2 '\[onboard\]' ~/.config/kwinrulesrc
```

The section must include `acceptfocus=false` and `acceptfocusrule=2`.

If it does, try reloading the rules:

```sh
qdbus6 org.kde.KWin /KWin reconfigure
```

### Titlebar/border still shown on KDE despite "Show window decoration" being off

This is expected with Onboard's current implementation, not a bug:
KWin ignores the GTK-side decoration hint for regular toplevels and
draws its own server-side decoration regardless. Add a `noborder` rule
for Onboard:

```sh
sed -i '/^\[onboard\]/a noborder = true\nnoborderrule = 2' ~/.config/kwinrulesrc
qdbus6 org.kde.KWin /KWin reconfigure
```

Then restart Onboard. Support for negotiating client-side decoration
via `xdg-decoration` (so the in-app preference works natively on KDE
too) is on the TODO list.

### Onboard cannot type and steals focus on GNOME

Maybe the bundled Onboard GNOME Shell extension failed to load, and Onboard also did not switch to XWayland.

The extension may stop working silently on some GNOME major bumps. 

Check:

```sh
gnome-extensions info onboard@onboard.local'
```

If `State: DISABLED`, re-enable with:

```sh
gnome-extensions enable onboard@onboard.local
```

If it fails to start citing an unsupported version, try to log out:
Onboard is supposed to update the version automatically, but extension may not restart until the next session. 

If it still fails, look into
`~/.local/share/gnome-shell/extensions/onboard@onboard.local/metadata.json`
and add your gnome-shell major version to the `shell-version` array if missing,
then log out.

If you'd rather not use the extension at all, disable it and Onboard
will auto-route through XWayland next launch:

```sh
gnome-extensions disable onboard@onboard.local
```
