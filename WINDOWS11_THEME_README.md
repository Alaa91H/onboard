# Windows 11 Touch Keyboard Theme for Onboard

This package adds a Windows 11-inspired on-screen keyboard theme to Onboard,
with a full floating keyboard mode matching the Windows 11 Touch Keyboard.

## Features

### Windows 11 Theme
- **Dark Theme**: Matches the Windows 11 dark mode touch keyboard
- **Light Theme**: Matches the Windows 11 light mode touch keyboard
- **Flat Design**: Modern flat key style with subtle gradients
- **Rounded Corners**: Windows 11-style rounded key corners
- **Accent Colors**: Blue accent color (#0078D4) for special keys
- **Segoe UI Font**: Uses the Windows 11 system font

### Floating Keyboard (Win11-Floating)
- **Always on Top**: Keyboard stays visible until you click the X close button
- **Number Row**: Western digits (1-0) at the top of the keyboard
- **Close Button**: X button to explicitly close the keyboard
- **Drag Handle**: Move the keyboard by dragging the title bar
- **Compact & Full Views**: Switch between different sizes

### Clipboard Manager
- **Copy/Cut/Paste**: Full clipboard action support
- **Clipboard History**: Keeps last 10 copied items
- **Pin Items**: Pin frequently used text snippets
- **Quick Paste**: Click any item to paste it instantly
- **Persistent Storage**: History saved across sessions

### Emoji Picker
- **8 Categories**: Smileys, Animals, Food, Activities, Travel, Objects, Symbols, Flags
- **Search**: Type to search emojis by name/category
- **Recent Emojis**: Track recently used emojis
- **Large Grid**: Easy-to-tap emoji buttons
- **Category Tabs**: Quick category navigation at top

### Long Press Alternatives
- **Accent Characters**: Long press vowels to get accented versions (à, á, â, ä, ã)
- **Arabic Diacritics**: Long press Arabic letters for tashkeel (َ, ُ, ِ, ّ, ْ)
- **Punctuation**: Long press period/comma for related symbols
- **3-Second Timeout**: Popup auto-closes after 3 seconds

### Arabic Language Support
- **Full Arabic Layout**: All 28 Arabic letters properly mapped
- **RTL Support**: Right-to-left text direction
- **Diacritics Layer**: Shift layer shows Arabic tashkeel marks
- **Western Digits**: Number row uses 0-9 (not Eastern Arabic numerals)
- **Arabic Punctuation**: Comma (،) and period (.) mapped correctly

### Professional Language Switching
- **Quick Toggle**: Click the language button to cycle EN ↔ AR
- **Language Menu**: Right-click for full language selection menu
- **Visual Feedback**: Button shows current language code
- **Layout Switching**: Automatically loads the correct keyboard layout
- **Remember Last**: Remembers last used language per session

## Installation

### Quick Install (Recommended)
```bash
chmod +x install_windows11_theme.sh
./install_windows11_theme.sh
```

### Manual Install

1. Copy the theme files to your Onboard themes directory:
   ```bash
   cp themes/Windows11*.theme ~/.local/share/onboard/themes/
   cp themes/Windows11*.colors ~/.local/share/onboard/themes/
   ```

2. Copy the layout files to your Onboard layouts directory:
   ```bash
   cp layouts/Win11-*.onboard ~/.local/share/onboard/layouts/
   cp layouts/Win11-*.svg ~/.local/share/onboard/layouts/
   ```

3. Copy the Python modules to your Onboard modules directory:
   ```bash
   cp Onboard/CompactMode.py ~/.local/share/onboard/Onboard/
   cp Onboard/KeyboardWidgetCompactPatch.py ~/.local/share/onboard/Onboard/
   cp Onboard/ClipboardManager.py ~/.local/share/onboard/Onboard/
   cp Onboard/EmojiPicker.py ~/.local/share/onboard/Onboard/
   cp Onboard/LanguageSwitcher.py ~/.local/share/onboard/Onboard/
   cp Onboard/FloatingWindowPatch.py ~/.local/share/onboard/Onboard/
   cp Onboard/Win11FloatingIntegration.py ~/.local/share/onboard/Onboard/
   cp Onboard/Win11KeyboardWidgetPatch.py ~/.local/share/onboard/Onboard/
   ```

4. Enable the features in your Onboard configuration:
   ```python
   # In your Onboard startup script or configuration
   from Onboard.Win11KeyboardWidgetPatch import apply_win11_css
   from Onboard.FloatingWindowPatch import patch_kbd_window
   apply_win11_css()
   ```

## Usage

### Selecting the Theme
1. Open Onboard Settings
2. Go to the "Theme" tab
3. Select "Windows11" or "Windows11 Light" from the theme list
4. Click "Apply"

### Using the Floating Keyboard
1. Open Onboard Settings
2. Go to the "Layout" tab
3. Select "Win11 Floating" (English) or "Win11 Arabic" (Arabic)
4. The keyboard appears floating and stays on top
5. Click **X** to close, or click **EN/AR** to switch language

### Keyboard Layout (Win11-Floating)
```
┌─────────────────────────────────────────────────────┐
│  ⋯ move                              EN  ✕ close   │  ← Title bar
├─────────────────────────────────────────────────────┤
│  1   2   3   4   5   6   7   8   9   0   ⌫       │  ← Number row
├─────────────────────────────────────────────────────┤
│    Q   W   E   R   T   Y   U   I   O   P          │  ← Row 1
├─────────────────────────────────────────────────────┤
│      A   S   D   F   G   H   J   K   L            │  ← Row 2
├─────────────────────────────────────────────────────┤
│  ⇧     Z   X   C   V   B   N   M        ⌫        │  ← Row 3
├─────────────────────────────────────────────────────┤
│ ?123  ,   😊  📋      SPACE      .     ENTER      │  ← Row 4
└─────────────────────────────────────────────────────┘
│              Word Suggestions Bar                   │
```

### Using Emoji Picker
1. Click the 😊 button on the keyboard
2. Browse categories or type to search
3. Click an emoji to insert it
4. Click 😊 again or click elsewhere to close

### Using Clipboard
1. Click the 📋 button on the keyboard
2. View clipboard history (up to 10 items)
3. Click "Paste" on any item to paste it
4. Click "Pin" to keep important items
5. Click "Clear All" to clear history

### Language Switching
- **Quick Switch**: Click the language button (EN/AR) to toggle
- **Menu**: Right-click the language button for full menu
- **Arabic Mode**: Keyboard switches to Arabic RTL layout

### Long Press for Alternatives
- **Hold a key** for 0.5 seconds to see alternatives
- Vowels show accented versions (à, á, â, ä, ã)
- Arabic letters show diacritics (َ, ُ, ِ, ّ, ْ)
- Popup auto-closes after 3 seconds

## File Structure

```
themes/
├── Windows11.theme              # Dark theme definition
├── Windows11 Dark.colors        # Dark color scheme
├── Windows11 Light.theme        # Light theme definition
└── Windows11 Light.colors       # Light color scheme

layouts/
├── Win11-Full.onboard           # Full English layout
├── Win11-Full-Alpha.svg         # Full keyboard SVG
├── Win11-Compact.onboard        # Compact keyboard layout
├── Win11-Compact-Alpha.svg      # Compact SVG geometry
├── Win11-Floating.onboard       # ★ Floating keyboard (all features)
├── Win11-Floating-Alpha.svg     # Floating keyboard SVG
├── Win11-Arabic.onboard         # Arabic RTL layout
└── Win11-Floating-Arabic-Alpha.svg  # Arabic SVG geometry

Onboard/
├── CompactMode.py               # Compact/minimized mode manager
├── KeyboardWidgetCompactPatch.py  # Widget integration patch
├── ClipboardManager.py          # ★ Clipboard history & paste
├── EmojiPicker.py               # ★ Searchable emoji picker
├── LanguageSwitcher.py          # ★ EN/AR language switching
├── FloatingWindowPatch.py       # ★ Always-on-top window behavior
├── Win11FloatingIntegration.py  # ★ Master integration module
└── Win11KeyboardWidgetPatch.py  # ★ Widget hooks & CSS styling
```

## Customization

### Changing Colors
Edit the `.colors` files to customize the color scheme:
- `rgb="#RRGGBB"` - Hex RGB color values
- `opacity="0.0-1.0"` - Transparency level
- States: `hover="true"`, `pressed="true"`, `active="true"`

### Adjusting Compact Mode
Edit `CompactMode.py` to change:
- `COMPACT_WIDTH_RATIO` - Width ratio for compact mode (default: 0.45)
- `COMPACT_HEIGHT_RATIO` - Height ratio for compact mode (default: 0.60)
- `MINI_WIDTH_RATIO` - Width ratio for mini mode (default: 0.25)
- `MINI_HEIGHT_RATIO` - Height ratio for mini mode (default: 0.35)

### Customizing Clipboard History
Edit `ClipboardManager.py`:
- `MAX_CLIPBOARD_HISTORY` - Max items to keep (default: 10)

### Adding New Languages
Edit `LanguageSwitcher.py`:
- Add entries to `SUPPORTED_LANGUAGES` dict
- Create corresponding `.onboard` layout file
- Create `-Alpha.svg` geometry file

### Adding Long Press Alternatives
Edit `Win11KeyboardWidgetPatch.py`:
- Add entries to `LONG_PRESS_ALTERNATIVES` dict in `Win11FloatingIntegration.py`

### Modifying Emoji Categories
Edit `EmojiPicker.py`:
- Modify `EMOJI_CATEGORIES` dict with new categories/emojis

### Adding Keyboard Shortcuts
Edit `KeyboardWidgetCompactPatch.py` to add custom shortcuts.

## Compatibility

- **Onboard Version**: 1.4.x and later
- **GTK Version**: 3.0
- **Python Version**: 3.6+
- **Operating System**: Linux (X11 and Wayland)

## Credits

- Original Onboard project: https://github.com/onboard-osk/onboard
- Windows 11 design inspiration: Microsoft Corporation
- Fluent Design System: https://www.microsoft.com/design/fluent/

## License

This theme and compact mode implementation are licensed under the same
terms as Onboard itself (GPL-3+).

## Support

For issues or suggestions, please open an issue on the project repository.
