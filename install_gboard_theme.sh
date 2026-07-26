#!/bin/bash
# Installation script for Gboard Theme for Onboard
# Based on Google Gboard / Material Design 3 design language

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() { echo -e "${GREEN}[INFO]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }
print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }

SCRIPT_DIR="$(cd -- "$(dirname "$0")" >/dev/null 2>&1; pwd -P)"

detect_onboard_dir() {
    local paths=(
        "$HOME/.local/share/onboard"
        "/usr/share/onboard"
        "/usr/local/share/onboard"
        "$HOME/.onboard"
    )
    for path in "${paths[@]}"; do
        if [ -d "$path" ]; then
            echo "$path"
            return 0
        fi
    done
    echo "$HOME/.local/share/onboard"
    return 1
}

main() {
    print_info "Installing Gboard Theme for Onboard..."
    print_info "Based on Google Material Design 3 / Material You"

    ONBOARD_DIR=$(detect_onboard_dir)

    if [ ! -d "$ONBOARD_DIR" ]; then
        print_warning "Onboard directory not found at $ONBOARD_DIR"
        print_info "Creating directory structure..."
        mkdir -p "$ONBOARD_DIR"/{themes,layouts}
    fi

    print_status "Using Onboard directory: $ONBOARD_DIR"

    print_status "Installing Gboard theme files..."
    cp -v "$SCRIPT_DIR/themes/Gboard.theme" "$ONBOARD_DIR/themes/" 2>/dev/null || true
    cp -v "$SCRIPT_DIR/themes/Gboard Dark.colors" "$ONBOARD_DIR/themes/" 2>/dev/null || true
    cp -v "$SCRIPT_DIR/themes/Gboard Light.colors" "$ONBOARD_DIR/themes/" 2>/dev/null || true
    print_status "Gboard theme files installed"

    print_status "Installing Gboard layout files..."
    if [ -d "$SCRIPT_DIR/layouts" ]; then
        cp -v "$SCRIPT_DIR/layouts/Gboard-"*.onboard "$ONBOARD_DIR/layouts/" 2>/dev/null || true
        cp -v "$SCRIPT_DIR/layouts/Gboard-"*.svg "$ONBOARD_DIR/layouts/" 2>/dev/null || true
        print_status "Gboard layout files installed"
    fi

    cat > "$ONBOARD_DIR/GBOARD_THEME_INFO.txt" << 'EOF'
Gboard Theme for Onboard
========================

Based on Google Gboard / Material Design 3 / Material You design language.

Theme Files:
- themes/Gboard.theme (Material Design 3 key styling)
- themes/Gboard Dark.colors (Material You dark colors)
- themes/Gboard Light.colors (Material You light colors)

Design Features:
- Material Design 3 (Material You) design language
- Google Blue (#4285F4) accent colors
- Rounded keys (45% roundness) matching Gboard
- Clean flat key style with subtle elevation
- Google Sans typography
- Material You surface colors with proper state layers

Color Palette (Dark):
- Background: #1B1B1F (Material You dark surface)
- Key Surface: #2B2F35 (surface variant)
- Accent: #4285F4 (Google Blue)
- Label: #E3E3E8 (light on dark)

Color Palette (Light):
- Background: #E8EAED (Material You light surface)
- Key Surface: #FFFFFF (pure white)
- Accent: #1A73E8 (Google Blue)
- Label: #202124 (dark on light)

To use:
1. Open Onboard Settings
2. Go to the 'Theme' tab
3. Select 'Gboard' theme
4. For dark mode, ensure color scheme is 'Gboard Dark'
5. For light mode, switch to 'Gboard Light'

Advanced Customization:
- Roundness: 45% (Gboard default)
- Key Style: Flat (Material Design)
- Key Size: 94% (slightly larger than default)
- Shadow: 8% strength, 6% size (subtle elevation)
EOF

    print_status "Installation completed successfully!"
    echo ""
    print_info "To use the Gboard theme:"
    print_info "1. Open Onboard Settings"
    print_info "2. Go to the 'Theme' tab"
    print_info "3. Select 'Gboard' (Dark) or create a custom theme with Gboard color scheme"
    print_info "4. For light mode, customize theme and select 'Gboard Light' color scheme"
    echo ""
    print_info "Theme features Material Design 3 design language with Google colors"
}

main "$@"
