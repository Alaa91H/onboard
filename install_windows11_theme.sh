#!/bin/bash
# Installation script for Windows 11 Touch Keyboard Theme for Onboard
# This script installs the theme, layouts, and compact mode module

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Print with color
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# Get the script directory
SCRIPT_DIR="$(cd -- "$(dirname "$0")" >/dev/null 2>&1; pwd -P)"

# Detect Onboard installation directory
detect_onboard_dir() {
    # Check common installation paths
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
    
    # If not found, create in user directory
    echo "$HOME/.local/share/onboard"
    return 1
}

# Main installation function
main() {
    print_info "Installing Windows 11 Touch Keyboard Theme for Onboard..."
    
    # Detect Onboard directory
    ONBOARD_DIR=$(detect_onboard_dir)
    
    if [ ! -d "$ONBOARD_DIR" ]; then
        print_warning "Onboard directory not found at $ONBOARD_DIR"
        print_info "Creating directory structure..."
        mkdir -p "$ONBOARD_DIR"/{themes,layouts,Onboard}
    fi
    
    print_status "Using Onboard directory: $ONBOARD_DIR"
    
    # Install theme files
    print_status "Installing theme files..."
    if [ -d "$SCRIPT_DIR/themes" ]; then
        cp -v "$SCRIPT_DIR/themes/"*.theme "$ONBOARD_DIR/themes/" 2>/dev/null || true
        cp -v "$SCRIPT_DIR/themes/"*.colors "$ONBOARD_DIR/themes/" 2>/dev/null || true
        print_status "Theme files installed successfully"
    else
        print_warning "Theme directory not found"
    fi
    
    # Install layout files
    print_status "Installing layout files..."
    if [ -d "$SCRIPT_DIR/layouts" ]; then
        cp -v "$SCRIPT_DIR/layouts/Win11-"*.onboard "$ONBOARD_DIR/layouts/" 2>/dev/null || true
        cp -v "$SCRIPT_DIR/layouts/Win11-"*.svg "$ONBOARD_DIR/layouts/" 2>/dev/null || true
        print_status "Layout files installed successfully"
    else
        print_warning "Layout directory not found"
    fi
    
    # Install all Onboard modules
    print_status "Installing Onboard modules..."
    if [ -d "$SCRIPT_DIR/Onboard" ]; then
        # Core compact mode
        cp -v "$SCRIPT_DIR/Onboard/CompactMode.py" "$ONBOARD_DIR/Onboard/" 2>/dev/null || true
        cp -v "$SCRIPT_DIR/Onboard/KeyboardWidgetCompactPatch.py" "$ONBOARD_DIR/Onboard/" 2>/dev/null || true
        
        # Win11 floating keyboard features
        cp -v "$SCRIPT_DIR/Onboard/ClipboardManager.py" "$ONBOARD_DIR/Onboard/" 2>/dev/null || true
        cp -v "$SCRIPT_DIR/Onboard/EmojiPicker.py" "$ONBOARD_DIR/Onboard/" 2>/dev/null || true
        cp -v "$SCRIPT_DIR/Onboard/LanguageSwitcher.py" "$ONBOARD_DIR/Onboard/" 2>/dev/null || true
        cp -v "$SCRIPT_DIR/Onboard/FloatingWindowPatch.py" "$ONBOARD_DIR/Onboard/" 2>/dev/null || true
        cp -v "$SCRIPT_DIR/Onboard/Win11FloatingIntegration.py" "$ONBOARD_DIR/Onboard/" 2>/dev/null || true
        cp -v "$SCRIPT_DIR/Onboard/Win11KeyboardWidgetPatch.py" "$ONBOARD_DIR/Onboard/" 2>/dev/null || true
        
        print_status "All modules installed successfully"
    else
        print_warning "Onboard module directory not found"
    fi
    
    # Create installation info
    print_status "Creating installation info..."
    cat > "$ONBOARD_DIR/WINDOWS11_THEME_INFO.txt" << EOF
Windows 11 Touch Keyboard Theme for Onboard
============================================

Installed: $(date)
Version: 1.0.0

Files installed:
Themes:
- themes/Windows11.theme
- themes/Windows11 Dark.colors
- themes/Windows11 Light.theme
- themes/Windows11 Light.colors

Layouts:
- layouts/Win11-Full.onboard (English full keyboard)
- layouts/Win11-Full-Alpha.svg
- layouts/Win11-Compact.onboard
- layouts/Win11-Compact-Alpha.svg
- layouts/Win11-Floating.onboard (Floating keyboard with all features)
- layouts/Win11-Floating-Alpha.svg
- layouts/Win11-Arabic.onboard (Arabic RTL keyboard)
- layouts/Win11-Floating-Arabic-Alpha.svg

Modules:
- Onboard/CompactMode.py (Compact/minimized mode)
- Onboard/KeyboardWidgetCompactPatch.py
- Onboard/ClipboardManager.py (Clipboard history & paste)
- Onboard/EmojiPicker.py (Searchable emoji picker)
- Onboard/LanguageSwitcher.py (EN/AR language switching)
- Onboard/FloatingWindowPatch.py (Always-on-top window)
- Onboard/Win11FloatingIntegration.py (Master integration)
- Onboard/Win11KeyboardWidgetPatch.py (Widget hooks & CSS)

Features:
- Always-on-top floating keyboard with close button
- Number row (Western digits 1-0) at top
- Emoji picker with categories and search
- Clipboard manager with history, pin, paste
- Long-press alternatives (diacritics, accents)
- English and Arabic (RTL) language support
- Professional language switcher (toggle + menu)
- Word suggestion bar integration

To use:
1. Open Onboard Settings
2. Select "Win11 Floating" layout
3. Keyboard stays on top until you click X to close
4. Use 😊 button for emoji, 📋 for clipboard
5. Click language button to switch EN/AR

For more information, see WINDOWS11_THEME_README.md
EOF
    
    print_status "Installation completed successfully!"
    echo ""
    print_info "To use the Windows 11 theme:"
    print_info "1. Open Onboard Settings"
    print_info "2. Go to the 'Theme' tab"
    print_info "3. Select 'Windows11' or 'Windows11 Light'"
    print_info "4. For compact mode, press Ctrl+Shift+C"
    echo ""
    print_info "For more information, see WINDOWS11_THEME_README.md"
}

# Run main function
main "$@"
