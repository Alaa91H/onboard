#!/bin/bash
# Installation script for Windows 11 Touch Keyboard Theme for Onboard
# This script installs the theme, layouts, and compact mode module

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

FAIL_COUNT=0
OK_COUNT=0
WARN_COUNT=0

print_ok()    { echo -e "${GREEN}[OK]${NC} $1"; OK_COUNT=$((OK_COUNT+1)); }
print_warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; WARN_COUNT=$((WARN_COUNT+1)); }
print_fail()  { echo -e "${RED}[FAIL]${NC} $1"; FAIL_COUNT=$((FAIL_COUNT+1)); }
print_info()  { echo -e "${BLUE}[INFO]${NC} $1"; }

safe_copy() {
    local src="$1"
    local dst="$2"
    local label="$3"

    if [ ! -f "$src" ]; then
        print_fail "Source not found: $src"
        return 1
    fi

    if [ ! -d "$(dirname "$dst")" ]; then
        mkdir -p "$(dirname "$dst")" || {
            print_fail "Cannot create directory: $(dirname "$dst")"
            return 1
        }
    fi

    if cp "$src" "$dst" 2>/dev/null; then
        print_ok "$label"
        return 0
    else
        print_fail "Failed to copy $label (permission denied?)"
        return 1
    fi
}

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
    print_info "Installing Windows 11 Touch Keyboard Theme for Onboard..."
    print_info ""

    ONBOARD_DIR=$(detect_onboard_dir)
    if [ ! -d "$ONBOARD_DIR" ]; then
        print_warn "Onboard directory not found at $ONBOARD_DIR — creating it"
        mkdir -p "$ONBOARD_DIR"/{themes,layouts,Onboard}
    fi

    print_info "Target directory: $ONBOARD_DIR"
    print_info ""

    # --- Themes ---
    print_info "--- Installing theme files ---"
    if [ -d "$SCRIPT_DIR/themes" ]; then
        for f in "$SCRIPT_DIR/themes/"Windows11*.theme "$SCRIPT_DIR/themes/"Windows11*.colors; do
            [ -f "$f" ] && safe_copy "$f" "$ONBOARD_DIR/themes/$(basename "$f")" "$(basename "$f")"
        done
    else
        print_warn "themes/ directory not found — skipping"
    fi

    # --- Layouts ---
    print_info ""
    print_info "--- Installing layout files ---"
    if [ -d "$SCRIPT_DIR/layouts" ]; then
        for f in "$SCRIPT_DIR/layouts/Win11-"*.onboard "$SCRIPT_DIR/layouts/Win11-"*.svg; do
            [ -f "$f" ] && safe_copy "$f" "$ONBOARD_DIR/layouts/$(basename "$f")" "$(basename "$f")"
        done
    else
        print_warn "layouts/ directory not found — skipping"
    fi

    # --- Modules ---
    print_info ""
    print_info "--- Installing Onboard modules ---"
    if [ -d "$SCRIPT_DIR/Onboard" ]; then
        MODULES=(
            "CompactMode.py"
            "KeyboardWidgetCompactPatch.py"
            "ClipboardManager.py"
            "EmojiPicker.py"
            "LanguageSwitcher.py"
            "FloatingWindowPatch.py"
            "Win11FloatingIntegration.py"
            "Win11KeyboardWidgetPatch.py"
        )
        for mod in "${MODULES[@]}"; do
            safe_copy "$SCRIPT_DIR/Onboard/$mod" "$ONBOARD_DIR/Onboard/$mod" "$mod"
        done
    else
        print_warn "Onboard/ directory not found — skipping"
    fi

    # --- Summary ---
    print_info ""
    print_info "========================================="
    print_info "Installation complete."
    print_info "  OK:   $OK_COUNT"
    print_info "  WARN: $WARN_COUNT"
    print_info "  FAIL: $FAIL_COUNT"
    print_info "========================================="

    if [ "$FAIL_COUNT" -gt 0 ]; then
        print_info ""
        print_info "Some files failed to copy. Possible causes:"
        print_info "  - Onboard is not installed"
        print_info "  - Permission denied (try: sudo $0)"
        print_info "  - Running from wrong directory"
        print_info ""
        print_info "You can still use Onboard normally."
        print_info "The Win11 theme features require these files to be"
        print_info "in the Onboard package directory."
        exit 1
    fi

    print_info ""
    print_info "To use the Windows 11 theme:"
    print_info "  1. Open Onboard Settings"
    print_info "  2. Go to the 'Theme' tab"
    print_info "  3. Select 'Windows11' or 'Windows11 Light'"
    print_info "  4. For floating keyboard, select 'Win11-Floating' layout"
    print_info "  5. For Arabic, select 'Win11-Arabic' layout"
    print_info ""
    print_info "For more information, see WINDOWS11_THEME_README.md"
}

main "$@"
