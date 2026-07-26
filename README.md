# Onboard 1.4.4

![Onboard](https://github.com/onboard-osk/onboard/blob/main/onboard.png)

Onboard is a professional on-screen keyboard for Linux desktops. It acts as a native part of the system -- its tray icon lives permanently in the top panel bar, and the keyboard language automatically follows the system input language. Onboard supports X11 (full) and Wayland (experimental).

**Table of Contents**

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Supported Languages](#supported-languages)
- [Themes](#themes)
- [Layouts](#layouts)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Building from Source](#building-from-source)
- [Packaging](#packaging)
- [CI/CD Pipeline](#cicd-pipeline)
- [GNOME Shell Extension](#gnome-shell-extension)
- [D-Bus Interface](#dbus-interface)
- [GSettings Schema](#gsettings-schema)
- [Configuration Files](#configuration-files)
- [Development Guide](#development-guide)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Overview

Onboard provides a fully functional on-screen keyboard that:

- **Lives in the top panel bar** -- A permanent tray icon (keyboard symbol + language indicator) sits in the system tray. Click it to toggle the keyboard.
- **Follows system language** -- When you switch the system input language (e.g., via `setxkbmap`, GNOME keyboard settings, or KDE input method), Onboard automatically switches its layout to match. This makes it behave as a native part of the desktop.
- **Stays on top** -- The floating keyboard window stays above all other windows at all times. It is draggable and only closes via the X button.
- **Works everywhere** -- X11 (full), Wayland with GNOME Mutter and KDE Plasma (experimental), Flatpak, Snap, Debian/Ubuntu .deb, and Fedora RPM.

---

## Key Features

| Feature | Description |
|---------|-------------|
| **System Tray Icon** | Permanent icon in top panel with language indicator (e.g., "EN", "AR", "FR"). Left-click toggles keyboard. Right-click opens context menu (Show/Hide, Preferences, Help, Quit). |
| **Language Auto-Sync** | Keyboard layout follows the system's active input language via D-Bus and AT-SPI. No manual configuration needed. |
| **40 World Languages** | English, Arabic, French, German, Spanish, Portuguese, Italian, Dutch, Russian, Ukrainian, Chinese, Japanese, Korean, Hebrew, Persian, Urdu, Hindi, Turkish, Polish, Swedish, Danish, Norwegian, Finnish, Czech, Romanian, Hungarian, Greek, Thai, Vietnamese, Indonesian, Malay, Bengali, Swahili, Kannada, Tamil, Telugu, Malayalam, Marathi, Gujarati, Punjabi. |
| **Floating Mode** | Keyboard always stays on top. Draggable. Resizable. Closes only via X button. |
| **Clipboard Manager** | Persistent clipboard with up to 1000 items (configurable). Stores text history as JSON. |
| **Emoji Picker** | Full emoji keyboard with categories, search, and recent emojis. |
| **Long-Press Keys** | Hold a key to access diacritics, accents, and alternative characters. |
| **Number Row** | Optional top row showing 0-9 for quick number entry. |
| **Word Suggestions** | On-device n-gram language model for word completion and prediction. Fast (<10ms), low memory (<30MB). |
| **RTL Support** | Full right-to-left layout for Arabic, Hebrew, Persian, and Urdu. |
| **Multi-Theme** | 16 themes + 18 color schemes including Windows 11, Gboard (Material Design 3), Dark, Light, High Contrast, and more. |
| **Wayland Support** | Experimental support via gtk-layer-shell for GNOME Mutter, KDE Plasma, and wlroots-based compositors. |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    GNOME Shell Panel                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ [⌨ EN]  Onboard Indicator Extension                │    │
│  │  icon  language   (extension.js)                    │    │
│  └──────────────┬──────────────────────────────────────┘    │
│                 │ D-Bus                                      │
├─────────────────┼────────────────────────────────────────────┤
│                 ▼                                             │
│  ┌──────────────────────────────────────────────────────┐    │
│  │              Onboard GTK Application                  │    │
│  │                                                       │    │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │    │
│  │  │Indicator │  │Keyboard  │  │ LanguageSwitcher  │  │    │
│  │  │(Systray) │  │Widget    │  │ (40 languages)    │  │    │
│  │  └────┬─────┘  └────┬─────┘  └────────┬─────────┘  │    │
│  │       │              │                 │              │    │
│  │  ┌────┴──────────────┴─────────────────┴──────────┐  │    │
│  │  │              KbdWindow (Floating)               │  │    │
│  │  │  ┌─────────────────────────────────────────┐   │  │    │
│  │  │  │  Layout SVG + Key Definitions + Themes   │   │  │    │
│  │  │  └─────────────────────────────────────────┘   │  │    │
│  │  └───────────────────────────────────────────────┘  │    │
│  │                                                       │    │
│  │  Modules: Config, AutoShow, AutoHide, Scanner,       │    │
│  │  ClickSimulator, SpellChecker, EmojiPicker,          │    │
│  │  ClipboardManager, TextContext, Sound                 │    │
│  └──────────────────────────────────────────────────────┘    │
│                                                               │
│  ┌──────────────────────────────────────────────────────┐    │
│  │           OSK Native C Module (osk/)                  │    │
│  │  osk_audio, osk_click_mapper, osk_dconf, osk_devices,│    │
│  │  osk_hunspell, osk_struts, osk_udev, osk_uinput,    │    │
│  │  osk_virtkey, osk_virtkey_x, osk_virtkey_wayland    │    │
│  └──────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────┘
```

### Core Components

| Component | File | Purpose |
|-----------|------|---------|
| **Main Controller** | `OnboardGtk.py` | Application entry point, D-Bus registration, single-instance check, keyboard lifecycle |
| **Keyboard Window** | `KbdWindow.py` | Floating window that stays on top, draggable, handles docking |
| **Keyboard Logic** | `Keyboard.py` (3198 lines) | Key events, modifiers, key synthesis, dock modes, scanner, layers |
| **Keyboard Widget** | `KeyboardWidget.py` | GTK rendering of the keyboard, key layout, visual feedback |
| **Indicator** | `Indicator.py` | System tray icon (AppIndicator3 / GtkStatusIcon), context menu, language tooltip |
| **Language Switcher** | `LanguageSwitcher.py` (685 lines) | 40-language dictionary, toggle/cycle/set language, RTL detection, layout mapping |
| **Layout Engine** | `Layout.py`, `LayoutLoaderSVG.py` | SVG-based keyboard layout loading and rendering |
| **Config** | `Config.py`, `ConfigUtils.py` | GSettings-backed configuration, theme/layout management |
| **Word Suggestions** | `WordSuggestions.py`, `WPEngine.py` | N-gram language model prediction, on-device learning |
| **Emoji Picker** | `EmojiPicker.py`, `emoji_data.py` | Full emoji keyboard with categories and search |
| **Clipboard** | `ClipboardManager.py` | Persistent clipboard history (100-1000 items, JSON storage) |
| **Sound** | `Sound.py` | Key press audio feedback via libcanberra |
| **Spell Checker** | `SpellChecker.py` | Hunspell-based spell checking |
| **Auto Show/Hide** | `AutoShow.py`, `AutoHide.py` | Automatic keyboard visibility based on focus |
| **AT-SPI** | `AtspiStateTracker.py`, `TextContext.py` | Accessibility interface for system language detection |
| **Wayland** | `WaylandUtils.py`, `WaylandGnomeExtensionUtils.py` | Wayland session detection, layer-shell integration |
| **Native Module** | `osk/` (C) | Low-level uinput, device tracking, D-Bus helpers, audio, struts |

---

## Supported Languages

Onboard supports **40 languages** with automatic system input language synchronization:

| Code | Language | Native Name | Direction | Custom Layout |
|------|----------|-------------|-----------|---------------|
| `en` | English | English | LTR | Win11-Floating.onboard |
| `ar` | Arabic | العربية | **RTL** | Win11-Arabic.onboard |
| `fr` | French | Français | LTR | System XKB |
| `de` | German | Deutsch | LTR | System XKB |
| `es` | Spanish | Español | LTR | System XKB |
| `pt` | Portuguese | Português | LTR | System XKB |
| `it` | Italian | Italiano | LTR | System XKB |
| `nl` | Dutch | Nederlands | LTR | System XKB |
| `ru` | Russian | Русский | LTR | System XKB |
| `uk` | Ukrainian | Українська | LTR | System XKB |
| `zh` | Chinese | 中文 | LTR | System XKB |
| `ja` | Japanese | 日本語 | LTR | System XKB |
| `ko` | Korean | 한국어 | LTR | System XKB |
| `he` | Hebrew | עברית | **RTL** | System XKB |
| `fa` | Persian | فارسی | **RTL** | System XKB |
| `ur` | Urdu | اردو | **RTL** | System XKB |
| `hi` | Hindi | हिन्दी | LTR | System XKB |
| `tr` | Turkish | Türkçe | LTR | System XKB |
| `pl` | Polish | Polski | LTR | System XKB |
| `sv` | Swedish | Svenska | LTR | System XKB |
| `da` | Danish | Dansk | LTR | System XKB |
| `no` | Norwegian | Norsk | LTR | System XKB |
| `fi` | Finnish | Suomi | LTR | System XKB |
| `cs` | Czech | Čeština | LTR | System XKB |
| `ro` | Romanian | Română | LTR | System XKB |
| `hu` | Hungarian | Magyar | LTR | System XKB |
| `el` | Greek | Ελληνικά | LTR | System XKB |
| `th` | Thai | ไทย | LTR | System XKB |
| `vi` | Vietnamese | Tiếng Việt | LTR | System XKB |
| `id` | Indonesian | Bahasa Indonesia | LTR | System XKB |
| `ms` | Malay | Bahasa Melayu | LTR | System XKB |
| `bn` | Bengali | বাংলা | LTR | System XKB |
| `sw` | Swahili | Kiswahili | LTR | System XKB |
| `kn` | Kannada | ಕನ್ನಡ | LTR | System XKB |
| `ta` | Tamil | தமிழ் | LTR | System XKB |
| `te` | Telugu | తెలుగు | LTR | System XKB |
| `ml` | Malayalam | മലയാളം | LTR | System XKB |
| `mr` | Marathi | मराठी | LTR | System XKB |
| `gu` | Gujarati | ગુજરાતી | LTR | System XKB |
| `pa` | Punjabi | ਪੰਜਾਬੀ | LTR | System XKB |

**Language sync mechanism:** When the system input language changes, Onboard detects it through:
1. AT-SPI text context callbacks
2. XKB keyboard layout change events
3. D-Bus notifications from the GNOME Shell extension

Onboard then loads the matching layout and updates the tray indicator.

---

## Themes

Onboard ships with **16 themes** and **18 color schemes**:

### Theme Files (`.theme`)

| Theme | Style |
|-------|-------|
| Windows11 | Windows 11 Touch Keyboard style |
| Windows11 Light | Windows 11 light mode |
| Gboard | Google Gboard / Material Design 3 |
| Classic Onboard | Original Onboard design |
| HighContrast | High contrast accessibility |
| HighContrastInverse | Inverted high contrast |
| HighContrastInverseBlue | Blue inverted high contrast |
| DarkRoom | Dark theme for low-light |
| Nightshade | Deep purple dark theme |
| Ambiance | Ubuntu Ambiance style |
| AmbianceDark | Ubuntu Ambiance dark |
| Blackboard | Chalkboard dark theme |
| Droid | Android-inspired theme |
| ModelM | IBM Model M inspired |
| LowContrast | Soft low-contrast theme |
| Typist | Classic typewriter theme |
| Ronboard | Custom dark theme |

### Color Schemes (`.colors`)

| Scheme | Background | Accent | Style |
|--------|-----------|--------|-------|
| Windows11 Light | `#F3F3F3` | `#0078D4` | Light with blue accent |
| Windows11 Dark | `#2D2D2D` | `#60CDFF` | Dark with cyan accent |
| Gboard Light | `#E8EAED` | `#1A73E8` | Material You light |
| Gboard Dark | `#1B1B1F` | `#4285F4` | Material You dark |
| Classic Onboard | `#333333` | `#DD4814` | Orange accent dark |
| HighContrast | `#000000` | `#FFFFFF` | Pure black/white |
| Aubergine | `#2C001E` | `#E95420` | Ubuntu purple/orange |
| Charcoal | `#3C3C3C` | `#F4A261` | Warm charcoal |
| Granite | `#F0F0F0` | `#6C5CE7` | Light purple accent |
| ModelM | `#D4C5A9` | `#8B7355` | Beige retro |
| Typist | `#F5F5DC` | `#556B2F` | Parchment green |
| DarkRoom | `#1A1A2E` | `#E94560` | Navy/red accent |
| Black | `#000000` | `#00FF00` | Terminal green |
| LowContrast | `#4A4A4A` | `#90EE90` | Soft contrast |
| HighContrastInverseBlack | `#FFFFFF` | `#000000` | Inverted HC |
| HighContrastInverseBlue | `#FFFFFF` | `#0000FF` | Blue inverted HC |

### Gboard Theme (Material Design 3)

The Gboard theme implements Google's Material Design 3 / Material You:

- **Key roundness:** 45%
- **Key style:** Flat with subtle 8% shadow
- **Typography:** Google Sans
- **Dark palette:** Background `#1B1B1F`, Surface `#2B2F35`, Accent `#4285F4`
- **Light palette:** Background `#E8EAED`, Surface `#FFFFFF`, Accent `#1A73E8`

Install with: `bash install_gboard_theme.sh`

---

## Layouts

Onboard uses SVG-based keyboard layouts (`.onboard` XML files referencing `.svg` background layers):

| Layout | Description |
|--------|-------------|
| `Win11-Floating.onboard` | Windows 11 floating keyboard (English) |
| `Win11-Floating-Arabic.onboard` | Windows 11 floating keyboard (Arabic RTL) |
| `Win11-Full.onboard` | Windows 11 full-width keyboard |
| `Win11-Compact.onboard` | Windows 11 compact keyboard |
| `Gboard-Floating.onboard` | Google Gboard floating (English) |
| `Gboard-Floating-Arabic.onboard` | Google Gboard floating (Arabic RTL) |
| `Full-Keyboard.onboard` | Full traditional keyboard |
| `Compact.onboard` | Compact keyboard |
| `Phone.onboard` | Phone-style keyboard |
| `Small.onboard` | Small footprint keyboard |
| `Grid.onboard` | Grid-based keyboard |
| `Whiteboard.onboard` | Whiteboard-style keyboard |
| `Whiteboard_wide.onboard` | Wide whiteboard keyboard |
| `French_diacritics.onboard` | French with diacritics layer |
| `Full-Emoji-Keyboard.onboard` | Full emoji keyboard layout |

### Custom Layouts

Create new layouts by:
1. Copy an existing `.onboard` file
2. Edit the XML to change key positions, sizes, and labels
3. Create corresponding SVG background files
4. Place both in the `layouts/` directory

Layout XML structure:
```xml
<keyboard>
  <layer name="default" svg="Layout-Alpha.svg">
    <key label="a" x="0" y="0" w="1" h="1"/>
    <key label="b" x="1" y="0" w="1" h="1"/>
    <!-- ... -->
  </layer>
  <layer name="shift" svg="Layout-Shift.svg">
    <!-- shifted keys -->
  </layer>
</keyboard>
```

---

## Project Structure

```
onboard/
├── Onboard/                          # Main Python package (56 modules)
│   ├── __init__.py
│   ├── OnboardGtk.py                 # Application entry point + D-Bus service
│   ├── Keyboard.py                   # Core keyboard logic (3198 lines)
│   ├── KeyboardWidget.py             # GTK keyboard rendering
│   ├── KbdWindow.py                  # Floating window management
│   ├── Indicator.py                  # System tray icon (AppIndicator/GtkStatusIcon)
│   ├── LanguageSwitcher.py           # 40-language support + switching
│   ├── Config.py                     # GSettings configuration
│   ├── Layout.py                     # Keyboard layout model
│   ├── LayoutLoaderSVG.py           # SVG layout loader
│   ├── LayoutView.py                 # Layout rendering view
│   ├── Appearance.py                 # Theme/color scheme management
│   ├── AutoShow.py                   # Auto-show keyboard on focus
│   ├── AutoHide.py                   # Auto-hide keyboard
│   ├── WordSuggestions.py            # Word suggestion engine
│   ├── WPEngine.py                   # N-gram prediction engine
│   ├── EmojiPicker.py               # Emoji keyboard
│   ├── emoji_data.py                 # Emoji database
│   ├── ClipboardManager.py          # Clipboard history
│   ├── CharacterPalette.py          # Character palette panel
│   ├── SpellChecker.py              # Hunspell spell checker
│   ├── ClickSimulator.py            # Mouse click simulation
│   ├── Scanner.py                   # Switch access scanner
│   ├── Sound.py                     # Audio feedback
│   ├── TextContext.py               # AT-SPI text context
│   ├── TextDomain.py                # i18n text domain
│   ├── TextChanges.py               # Text change tracking
│   ├── GlobalKeyListener.py         # Global keyboard listener
│   ├── AtspiStateTracker.py        # AT-SPI state tracking
│   ├── UDevTracker.py              # udev device tracking
│   ├── HardwareSensorTracker.py    # Hardware sensor monitoring
│   ├── XInput.py                    # XInput2 integration
│   ├── DBusUtils.py                 # D-Bus utilities
│   ├── WaylandUtils.py             # Wayland session utilities
│   ├── WaylandGnomeExtensionUtils.py # GNOME Shell extension utils
│   ├── Win11FloatingIntegration.py  # Windows 11 floating mode
│   ├── Win11KeyboardWidgetPatch.py  # Windows 11 widget patch
│   ├── FloatingWindowPatch.py       # Floating window patch
│   ├── KeyboardWidgetCompactPatch.py # Compact widget patch
│   ├── CompactMode.py               # Compact mode manager
│   ├── KeyboardPopups.py            # Touch feedback popups
│   ├── TouchHandles.py             # Touch resize handles
│   ├── TouchInput.py               # Touch input handling
│   ├── IconPalette.py              # Icon palette panel
│   ├── UnicodeData.py              # Unicode character data
│   ├── canonical_equivalents.py    # Unicode canonical equivalents
│   ├── definitions.py              # Constants and enums
│   ├── exceptions.py               # Custom exceptions
│   ├── settings.py                 # Settings definitions
│   ├── utils.py                    # Utility functions
│   ├── Version.py                  # Version info
│   ├── osk/                         # Native C module
│   │   ├── osk_module.c/h         # Python C extension
│   │   ├── osk_audio.c            # Audio feedback
│   │   ├── osk_click_mapper.c     # Click mapping
│   │   ├── osk_dconf.c            # DConf integration
│   │   ├── osk_devices.c          # Device detection
│   │   ├── osk_hunspell.c         # Hunspell binding
│   │   ├── osk_struts.c           # Window struts
│   │   ├── osk_udev.c             # udev monitoring
│   │   ├── osk_uinput.c/h         # uinput device
│   │   ├── osk_util.c             # Utilities
│   │   ├── osk_virtkey.c/h        # Virtual key injection
│   │   ├── osk_virtkey_x.c/h      # X11 virtual keys
│   │   └── osk_virtkey_wayland.c/h # Wayland virtual keys
│   ├── pypredict/                   # N-gram prediction engine
│   │   ├── lm_wrapper.py           # Language model wrapper
│   │   ├── lm/                     # Language model data
│   │   ├── tools/                  # Training tools
│   │   └── test/                   # Prediction tests
│   └── test/                        # Unit tests
│
├── layouts/                          # Keyboard layouts
│   ├── *.onboard                    # 15 layout definitions
│   ├── *.svg                        # 51 SVG background layers
│   ├── images/                      # 21 icon SVGs
│   ├── key_defs.xml                 # Key definitions
│   └── word_suggestions.xml        # Word suggestion config
│
├── themes/                           # Themes and color schemes
│   ├── *.theme                      # 17 theme files
│   └── *.colors                     # 17 color scheme files
│
├── icons/                            # Application icons
│   ├── hicolor/                     # Standard icon theme
│   │   ├── 16/, 22/, 24/, 28/, 32/ # PNG sizes
│   │   ├── scalable/               # SVG icon
│   │   └── symbolic/               # Symbolic SVG
│   ├── HighContrast/               # High contrast icon
│   ├── ubuntu-mono-dark/           # Dark panel icon
│   └── ubuntu-mono-light/          # Light panel icon
│
├── gnome/                            # GNOME Shell extensions
│   ├── current/                     # GNOME 45+ (ES modules)
│   │   └── Onboard_Indicator@onboard.org/
│   │       ├── extension.js         # Panel indicator + D-Bus proxy
│   │       ├── stylesheet.css       # Panel styling
│   │       └── metadata.json        # Extension metadata
│   └── legacy/                      # GNOME 3.x (legacy)
│       └── Onboard_Indicator@onboard.org/
│
├── data/                             # Application data
│   └── org.onboard.gschema.xml     # GSettings schema (903 lines)
│
├── packaging/                        # Package build configs
│   ├── flatpak/
│   │   └── org.onboard.Onboard.yml  # Flatpak manifest
│   ├── snap/
│   │   └── snapcraft.yaml           # Snap build config
│   └── fedora/
│       └── onboard.spec             # RPM spec file
│
├── debian/                           # Debian packaging
│   ├── control                      # Package dependencies
│   ├── rules                        # Build rules
│   └── ...
│
├── po/                               # Translations (96 .po files)
│   ├── ar.po                        # Arabic
│   ├── fr.po                        # French
│   ├── de.po                        # German
│   └── ...                          # 93 more languages
│
├── scripts/                          # Build and utility scripts
│   ├── gen_gschema.py              # GSettings schema generator
│   ├── gen_unicode_data.py         # Unicode data generator
│   ├── sokSettings.py              # Settings launcher
│   └── toggle-onboard-hoverclick   # Hover click toggle
│
├── C/                                # User documentation (Mallard)
│   ├── index.page
│   ├── overview.page
│   └── ...                          # Help pages
│
├── man/                              # Man pages
│   ├── onboard.1
│   └── onboard-settings.1
│
├── docs/                             # Additional documentation
│
├── .github/
│   └── workflows/
│       └── build-packages.yml        # CI/CD pipeline
│
├── setup.py                          # Python build script
├── Makefile                          # Make targets
├── install_gboard_theme.sh           # Gboard theme installer
├── README.md                         # This file
├── README.WAYLAND.md                 # Wayland setup guide
├── README.FreeBSD.md                 # FreeBSD guide
├── DBUS.md                           # D-Bus API reference
├── CHANGELOG                         # Version history
└── COPYING                           # GPLv3 license
```

---

## Installation

### Debian / Ubuntu

```bash
# Remove any existing Onboard installation
sudo apt purge onboard onboard-common onboard-data mousetweaks

# Install from GitHub Release
# Download onboard-X.X.X-debian-amd64.deb from:
# https://github.com/Alaa91H/onboard/releases

sudo dpkg -i onboard-1.4.4-debian-amd64.deb
sudo apt-get install -f   # fix dependencies if needed
```

### Fedora

```bash
# Download onboard-X.X.X-fedora-x86_64.rpm from:
# https://github.com/Alaa91H/onboard/releases

sudo rpm -i onboard-1.4.4-fedora-x86_64.rpm
```

### Flatpak

```bash
# Download onboard-X.X.X-flatpak-x86_64.flatpak from:
# https://github.com/Alaa91H/onboard/releases

flatpak install onboard-1.4.4-flatpak-x86_64.flatpak
flatpak run org.onboard.Onboard
```

### Snap

```bash
# Download onboard-X.X.X-snap-amd64.snap from:
# https://github.com/Alaa91H/onboard/releases

sudo snap install onboard-1.4.4-snap-amd64.snap --dangerous
```

### Gboard Theme

```bash
bash install_gboard_theme.sh
```

---

## Building from Source

### Prerequisites

```bash
# Ubuntu / Debian
sudo apt install git build-essential python3-packaging python3-dev
sudo apt install dh-python python3-distutils-extra devscripts pkg-config
sudo apt install libgtk-3-dev libxtst-dev libxkbfile-dev libdconf-dev libcanberra-dev
sudo apt install libhunspell-dev libudev-dev python3-gi-cairo

# Fedora
sudo dnf install gcc-c++ python3-devel python3-setuptools python3-packaging
sudo dnf install python3-distutils-extra gtk3-devel libXtst-devel libxkbfile-devel
sudo dnf install dconf-devel libcanberra-devel hunspell-devel libudev-devel
sudo dnf install intltool pkg-config desktop-file-utils

# Arch Linux
sudo pacman -S base-devel git python-packaging python-distutils-extra dconf gtk3
sudo pacman -S libcanberra hunspell python-gobject iso-codes python-cairo librsvg python-dbus
```

### Build

```bash
git clone https://github.com/Alaa91H/onboard.git
cd onboard
python3 setup.py clean
python3 setup.py build
sudo python3 setup.py install
```

### Build Debian Packages

```bash
dpkg-buildpackage -us -uc -b
# Packages appear in parent directory
```

---

## Packaging

### Debian Packages

| Package | Architecture | Contents |
|---------|-------------|----------|
| `onboard-data` | all | Layouts, themes, icons, translations |
| `onboard` | any | Python modules, C extension, binaries |
| `onboard-common` | all | Common files |
| `gnome-shell-extension-onboard` | all | GNOME Shell extension |

### Fedora RPM

| Package | Architecture | Contents |
|---------|-------------|----------|
| `onboard` | x86_64 / aarch64 | Main package |
| `onboard-data` | noarch | Layouts, themes, icons |

### Release Asset Naming

```
onboard-{version}-debian-{arch}.deb       # e.g., onboard-1.4.4-debian-amd64.deb
onboard-{version}-fedora-{arch}.rpm       # e.g., onboard-1.4.4-fedora-x86_64.rpm
onboard-{version}-flatpak-{arch}.flatpak  # e.g., onboard-1.4.4-flatpak-x86_64.flatpak
onboard-{version}-snap-{arch}.snap        # e.g., onboard-1.4.4-snap-amd64.snap
```

---

## CI/CD Pipeline

GitHub Actions runs on every push and tag:

```
push to main / tag v* / PR
        │
        ▼
   ┌─────────┐
   │  Lint   │  flake8, py_compile, YAML/XML validation, structure check
   └────┬────┘
        │
   ┌────┴──────────────────────────────────────────────────┐
   │                    Matrix Builds                       │
   ├──────────────┬──────────────┬──────────────┬──────────┤
   │   Debian     │   Fedora     │   Flatpak    │   Snap   │
   │   (amd64)    │  x86_64 +    │  x86_64 +    │ amd64 +  │
   │              │  aarch64     │  aarch64     │ arm64    │
   └──────┬───────┴──────┬───────┴──────┬───────┴────┬─────┘
          │              │              │             │
          └──────────────┴──────────────┴─────────────┘
                                │
                                ▼
                      ┌─────────────────┐
                      │  GitHub Release  │  Auto-publishes on tag push
                      │  (7 packages)    │
                      └─────────────────┘
```

- **Node.js versions:** checkout@v5, setup-python@v6, upload-artifact@v6, download-artifact@v7, action-gh-release@v3
- **Validation:** Each package is validated with `dpkg-deb --info`, `rpm -qpi`, lintian checks
- **Release:** Automatic on `v*` tag push, 7 assets per release

---

## GNOME Shell Extension

The extension `Onboard_Indicator@onboard.org` provides:

- **Panel indicator:** Keyboard icon + language label (e.g., "EN") in the top bar
- **Language submenu:** Click to see all 40 supported languages
- **D-Bus bridge:** Communicates with Onboard via `org.onboard.Onboard.Keyboard`
- **GNOME keyboard override:** Hides GNOME's built-in keyboard, replaces with Onboard

### Installation

```bash
# GNOME 45+ (current)
cp -r gnome/current/Onboard_Indicator@onboard.org ~/.local/share/gnome-shell/extensions/

# GNOME 3.x (legacy)
cp -r gnome/legacy/Onboard_Indicator@onboard.org ~/.local/share/gnome-shell/extensions/

# Enable
gnome-extensions enable Onboard_Indicator@onboard.org
```

---

## D-Bus Interface

Onboard exposes a D-Bus service at `org.onboard.Onboard`:

| Method | Signature | Description |
|--------|-----------|-------------|
| `ToggleVisible` | `→` | Toggle keyboard visibility |
| `Show` | `→` | Show the keyboard |
| `Hide` | `→` | Hide the keyboard |
| `SetLanguage` | `s →` | Set keyboard language (e.g., "en", "ar") |
| `GetLanguage` | `→ s` | Get current language code |

### Example

```bash
# Toggle keyboard
dbus-send --session --type=method_call \
  --dest=org.onboard.Onboard \
  /org/onboard/Onboard/Keyboard \
  org.onboard.Onboard.Keyboard.ToggleVisible

# Set language to Arabic
dbus-send --session --type=method_call \
  --dest=org.onboard.Onboard \
  /org/onboard/Onboard/Keyboard \
  org.onboard.Onboard.Keyboard.SetLanguage \
  string:"ar"

# Get current language
dbus-send --session --type=method_call \
  --dest=org.onboard.Onboard \
  /org/onboard/Onboard/Keyboard \
  org.onboard.Onboard.Keyboard.GetLanguage
```

---

## GSettings Schema

Schema ID: `org.onboard`

### Key Settings

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `layout` | string | `''` | Current layout filename |
| `theme` | string | `''` | Current theme name |
| `color-scheme` | string | `''` | Current color scheme |
| `status-icon-provider` | enum | `auto` | Icon provider: `auto`, `GtkStatusIcon`, `AppIndicator` |
| `status-icon-left-click-action` | enum | `toggle` | Left-click: `toggle` or `menu` |
| `use-system-defaults` | boolean | `true` | Use system defaults for settings |
| `schema-version` | string | `''` | Schema version for migrations |

---

## Configuration Files

| File | Location | Purpose |
|------|----------|---------|
| GSettings | `~/.config/dconf/user` | Main configuration (binary) |
| Layouts | `~/.local/share/onboard/layouts/` | Custom keyboard layouts |
| Themes | `~/.local/share/onboard/themes/` | Custom themes and colors |
| Clipboard | `~/.local/share/onboard/clipboard.json` | Clipboard history |
| Language models | `~/.local/share/onboard/lm/` | N-gram prediction data |
| Autostart | `~/.config/autostart/onboard.desktop` | Auto-start on login |

---

## Development Guide

### Code Style

- Python 3 with `from __future__ import` for Python 2 compatibility
- PEP 8 with 4-space indentation
- Logging via `logging.getLogger("ModuleName")`
- Configuration via `Config()` singleton
- GTK 3 with `gi.repository` bindings
- D-Bus via `dbus` Python bindings

### Adding a New Language

1. Add entry to `SUPPORTED_LANGUAGES` in `LanguageSwitcher.py`:
```python
"xx": {
    "name": "LanguageName",
    "native_name": "NativeName",
    "layout_file": None,  # or custom .onboard file
    "icon": "XX",
    "direction": "ltr",   # or "rtl"
    "code": "xx",
    "use_system_layout": True,
},
```

2. Add label to `_LANG_LABELS` in `Indicator.py`
3. Add to `_LANG_CODES` in `extension.js` (GNOME Shell)
4. Add to `_langDisplayLabel()` in `extension.js`
5. Add to `_LANGUAGE_NAMES` in `extension.js`

### Adding a New Theme

1. Create `themes/MyTheme.theme`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<theme>
    <author>Your Name</author>
    <description>Theme description</description>
    <color_scheme>MyTheme</color_scheme>
    <key-roundness>45</key-roundness>
    <key-size>94</key-size>
    <shadow-strength>8</shadow-strength>
    <shadow-size>6</shadow-size>
</theme>
```

2. Create `themes/MyTheme.colors`:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<color_scheme>
    <author>Your Name</author>
    <description>Color description</description>
    <color name="key-bg" value="#FFFFFF"/>
    <color name="key-border" value="#CCCCCC"/>
    <color name="key-label" value="#333333"/>
    <color name="key-bg-active" value="#E0E0E0"/>
    <color name="window-bg" value="#F0F0F0"/>
    <color name="key-accent" value="#4285F4"/>
</color_scheme>
```

### Adding a New Layout

1. Create SVG background layers in `layouts/`
2. Create `.onboard` XML file referencing the SVGs
3. Place both files in `layouts/`
4. Register in `LanguageSwitcher.py` or use via GSettings

### Key Source Files to Modify

| Task | File(s) |
|------|---------|
| Add tray icon feature | `Indicator.py`, `extension.js` |
| Change language support | `LanguageSwitcher.py`, `extension.js` |
| Add keyboard layout | `layouts/*.onboard`, `layouts/*.svg` |
| Add theme | `themes/*.theme`, `themes/*.colors` |
| Modify key behavior | `Keyboard.py`, `KeyCommon.py`, `KeyGtk.py` |
| Change window behavior | `KbdWindow.py`, `FloatingWindowPatch.py` |
| Modify predictions | `WordSuggestions.py`, `WPEngine.py`, `pypredict/` |
| Change D-Bus API | `OnboardGtk.py`, `DBusUtils.py` |
| Modify GNOME extension | `gnome/current/.../extension.js` |
| Add translation | `po/*.po` |
| Modify build/packaging | `setup.py`, `packaging/` |

---

## Testing

```bash
# Unit tests
cd Onboard/test
python3 -m pytest

# Manual test tray icon
python3 -c "from Onboard.Indicator import Indicator; i = Indicator(); import Gtk; Gtk.main()"

# Test D-Bus interface
dbus-send --session --type=method_call \
  --dest=org.onboard.Onboard \
  /org/onboard/Onboard/Keyboard \
  org.onboard.Onboard.Keyboard.Show

# Test language switching
dbus-send --session --type=method_call \
  --dest=org.onboard.Onboard \
  /org/onboard/Onboard/Keyboard \
  org.onboard.Onboard.Keyboard.SetLanguage string:"ar"

# Validate XML layouts
for f in layouts/*.onboard; do python3 -c "import xml.etree.ElementTree as ET; ET.parse('$f'); print('OK: $f')"; done

# Validate YAML files
for f in $(find . -name "*.yml" -not -path "./.git/*"); do python3 -c "import yaml; yaml.safe_load(open('$f')); print('OK: $f')"; done
```

---

## Troubleshooting

### Keyboard doesn't appear

```bash
# Check if Onboard is running
pgrep onboard

# Start Onboard
onboard &

# Check D-Bus service
dbus-send --session --type=method_call \
  --dest=org.onboard.Onboard \
  /org/onboard/Onboard/Keyboard \
  org.onboard.Onboard.Keyboard.Show
```

### Tray icon not visible

```bash
# Check if AppIndicator3 is available
python3 -c "from gi.repository import AyatanaAppIndicator3; print('OK')"

# Or check GtkStatusIcon
python3 -c "from gi.repository import Gtk; print(Gtk.StatusIcon)"

# Check extension is enabled
gnome-extensions list --enabled | grep onboard
```

### Language not switching

```bash
# Check current XKB layout
setxkbmap -query

# Set a specific layout
setxkbmap -layout ar

# Check D-Bus language
dbus-send --session --type=method_call \
  --dest=org.onboard.Onboard \
  /org/onboard/Onboard/Keyboard \
  org.onboard.Onboard.Keyboard.GetLanguage
```

### Wayland issues

```bash
# Check if gtk-layer-shell is available
python3 -c "import gi; gi.require_version('GtkLayerShell', '1.0'); from gi.repository import GtkLayerShell; print('OK')"

# Enable uinput
sudo chmod 666 /dev/uinput
# Or create udev rule:
echo 'KERNEL=="uinput", MODE="0660", GROUP="input"' | sudo tee /etc/udev/rules.d/99-uinput.rules
```

---

## Manuals

```bash
# Terminal
man onboard
onboard -h

# Interactive help
yelp "help:onboard"
xdg-open "help:onboard"

# Right-click tray icon → Help
```

---

## Homepage

https://github.com/Alaa91H/onboard

## Reporting Bugs

https://github.com/Alaa91H/onboard/issues

## License

This program is released under the terms of the **GNU General Public License v3.0 or later** (GPLv3+). See the `COPYING` file for details.

Copyright (c) 2007-2017 Martin Boehme, Chris Jones, Francesco Fumanti, Gerd Kohlberger, marmuta
Copyright (c) 2026 Alaa91H
