//! Optional native primitives for Onboard.
//!
//! This first Rust milestone deliberately does not open `/dev/uinput` and does
//! not emit input events. It validates keymap/event data and keeps a bounded
//! state model behind a small PyO3 interface. Python remains responsible for
//! GTK, D-Bus, policy, localization, and selecting the established fallback.

use pyo3::exceptions::{PyRuntimeError, PyValueError};
use pyo3::prelude::*;
use std::collections::BTreeSet;

const MAX_KEYCODE: u32 = 767;
const MAX_KEYMAP_BYTES: usize = 1_048_576;

fn validate_keycode(keycode: u32) -> Result<(), String> {
    if keycode > MAX_KEYCODE {
        return Err(format!("invalid-keycode:{}", keycode));
    }
    Ok(())
}

fn validate_keymap(keymap: &[u8]) -> Result<(), String> {
    if keymap.is_empty() {
        return Err("invalid-keymap:empty".to_string());
    }
    if keymap.len() > MAX_KEYMAP_BYTES {
        return Err("invalid-keymap:too-large".to_string());
    }
    if std::str::from_utf8(keymap).is_err() {
        return Err("invalid-keymap:not-utf8".to_string());
    }
    if keymap.contains(&0) {
        return Err("invalid-keymap:contains-nul".to_string());
    }
    Ok(())
}

fn py_value_error(error: String) -> PyErr {
    PyValueError::new_err(error)
}

/// A bounded, in-memory state machine for a future native input backend.
///
/// The object intentionally records events only. A later milestone may add a
/// separately authorized `uinput` or Wayland transport behind the same Python
/// contract after real-session compatibility tests are in place.
#[pyclass(module = "Onboard.onboard_native")]
#[derive(Default)]
pub struct InputEngine {
    opened: bool,
    device_path: Option<String>,
    keymap: Option<Vec<u8>>,
    pressed: BTreeSet<u32>,
    modifiers: (u32, u32, u32, u32),
}

#[pymethods]
impl InputEngine {
    #[new]
    fn new() -> Self {
        Self::default()
    }

    /// Select a logical device path. This proof-of-concept never opens it.
    fn open(&mut self, device_path: &str) -> PyResult<()> {
        if device_path.trim().is_empty() {
            return Err(PyValueError::new_err("invalid-device-path"));
        }
        self.opened = true;
        self.device_path = Some(device_path.to_owned());
        Ok(())
    }

    /// Install and validate an UTF-8 keymap payload before events are accepted.
    fn install_keymap(&mut self, keymap_utf8: &[u8]) -> PyResult<()> {
        validate_keymap(keymap_utf8).map_err(py_value_error)?;
        self.keymap = Some(keymap_utf8.to_vec());
        Ok(())
    }

    /// Record a key transition after engine and keymap validation.
    fn key(&mut self, keycode: u32, pressed: bool, _timestamp_ms: u32) -> PyResult<()> {
        if !self.opened {
            return Err(PyRuntimeError::new_err("engine-not-open"));
        }
        if self.keymap.is_none() {
            return Err(PyRuntimeError::new_err("keymap-not-installed"));
        }
        validate_keycode(keycode).map_err(py_value_error)?;
        if pressed {
            self.pressed.insert(keycode);
        } else {
            self.pressed.remove(&keycode);
        }
        Ok(())
    }

    /// Store the compositor-synchronized modifier state for later transport.
    fn modifiers(&mut self, depressed: u32, latched: u32, locked: u32, group: u32) {
        self.modifiers = (depressed, latched, locked, group);
    }

    /// Reset all volatile state. This is safe to call more than once.
    fn close(&mut self) {
        self.opened = false;
        self.device_path = None;
        self.keymap = None;
        self.pressed.clear();
        self.modifiers = (0, 0, 0, 0);
    }

    #[getter]
    fn is_open(&self) -> bool {
        self.opened
    }

    #[getter]
    fn pressed_keycodes(&self) -> Vec<u32> {
        self.pressed.iter().copied().collect()
    }

    #[getter]
    fn modifier_state(&self) -> (u32, u32, u32, u32) {
        self.modifiers
    }

    #[getter]
    fn transport(&self) -> &'static str {
        "validation-only"
    }
}

#[pyfunction]
fn runtime_capabilities() -> Vec<&'static str> {
    vec!["keymap-validation", "event-state"]
}

#[pymodule]
fn onboard_native(module: &Bound<'_, PyModule>) -> PyResult<()> {
    module.add_class::<InputEngine>()?;
    module.add_function(wrap_pyfunction!(runtime_capabilities, module)?)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{validate_keycode, validate_keymap};

    #[test]
    fn accepts_a_small_utf8_keymap() {
        assert!(validate_keymap(b"xkb_keymap { xkb_keycodes \"(unnamed)\" {}; }\n").is_ok());
    }

    #[test]
    fn rejects_invalid_keymaps() {
        assert!(validate_keymap(b"").is_err());
        assert!(validate_keymap(&[0xff]).is_err());
        assert!(validate_keymap(b"xkb\0").is_err());
    }

    #[test]
    fn bounds_keycodes() {
        assert!(validate_keycode(0).is_ok());
        assert!(validate_keycode(767).is_ok());
        assert!(validate_keycode(768).is_err());
    }
}
