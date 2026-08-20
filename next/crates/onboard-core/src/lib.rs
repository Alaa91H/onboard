//! Platform-neutral state for the next independent Onboard application.
//!
//! This crate deliberately contains no GTK, Windows, macOS, D-Bus, or input
//! injection code. It makes the user-visible state deterministic and testable
//! before a platform bridge is permitted to perform a privileged operation.

/// Text direction selected by the active UI locale.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TextDirection {
    LeftToRight,
    RightToLeft,
}

/// Compact, platform-neutral presentation profile.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum KeyboardProfile {
    WindowsCompact,
}

/// Saved logical window geometry. A UI adapter maps it to the target display.
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct WindowGeometry {
    pub x: i32,
    pub y: i32,
    pub width: u32,
    pub height: u32,
}

impl Default for WindowGeometry {
    fn default() -> Self {
        Self {
            x: 36,
            y: 36,
            width: 860,
            height: 250,
        }
    }
}

/// State owned by the app, independent of a particular platform integration.
#[derive(Clone, Debug, Eq, PartialEq)]
pub struct KeyboardState {
    pub profile: KeyboardProfile,
    pub direction: TextDirection,
    pub visible: bool,
    pub geometry: WindowGeometry,
    pub requested_input_source: Option<String>,
}

impl Default for KeyboardState {
    fn default() -> Self {
        Self {
            profile: KeyboardProfile::WindowsCompact,
            direction: TextDirection::LeftToRight,
            visible: true,
            geometry: WindowGeometry::default(),
            requested_input_source: None,
        }
    }
}

impl KeyboardState {
    pub fn set_locale(&mut self, locale: &str) {
        let language = locale.split(['_', '-', '.']).next().unwrap_or_default();
        self.direction = match language {
            "ar" | "fa" | "he" | "ur" => TextDirection::RightToLeft,
            _ => TextDirection::LeftToRight,
        };
    }

    pub fn toggle_visibility(&mut self) {
        self.visible = !self.visible;
    }

    pub fn save_geometry(&mut self, geometry: WindowGeometry) {
        self.geometry = WindowGeometry {
            width: geometry.width.max(320),
            height: geometry.height.max(120),
            ..geometry
        };
    }

    pub fn request_input_source(&mut self, identifier: impl Into<String>) {
        let identifier = identifier.into();
        self.requested_input_source = (!identifier.trim().is_empty()).then_some(identifier);
    }
}

#[cfg(test)]
mod tests {
    use super::{KeyboardState, TextDirection, WindowGeometry};

    #[test]
    fn arabic_uses_rtl_without_changing_the_keyboard_profile() {
        let mut state = KeyboardState::default();
        state.set_locale("ar_SA.UTF-8");
        assert_eq!(TextDirection::RightToLeft, state.direction);
    }

    #[test]
    fn geometry_has_a_safe_minimum() {
        let mut state = KeyboardState::default();
        state.save_geometry(WindowGeometry {
            x: 0,
            y: 0,
            width: 1,
            height: 2,
        });
        assert_eq!(320, state.geometry.width);
        assert_eq!(120, state.geometry.height);
    }

    #[test]
    fn input_source_request_can_be_cleared() {
        let mut state = KeyboardState::default();
        state.request_input_source("com.example.arabic");
        assert!(state.requested_input_source.is_some());
        state.request_input_source("   ");
        assert!(state.requested_input_source.is_none());
    }
}
