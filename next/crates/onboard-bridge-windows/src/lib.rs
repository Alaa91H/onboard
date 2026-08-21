//! Windows bridge for the next independent Onboard application.
//!
//! `SendInput` can be blocked by User Interface Privilege Isolation (UIPI), so
//! a return value is never presented as an unconditional permission guarantee.
//! Windows input-source selection remains read-only until a TSF adapter can
//! select a source for the focused target without simulating user shortcuts.

use onboard_bridge_api::{BridgeCapabilities, BridgeError, PlatformBridge};
#[cfg(windows)]
use onboard_bridge_api::{Capability, Platform};

#[derive(Default)]
pub struct WindowsBridge;

impl WindowsBridge {
    pub const fn new() -> Self {
        Self
    }
}

#[cfg(windows)]
mod native {
    #[repr(C)]
    #[derive(Clone, Copy)]
    struct KeybdInput {
        virtual_key: u16,
        scan_code: u16,
        flags: u32,
        time: u32,
        extra_info: usize,
    }

    #[repr(C)]
    #[derive(Clone, Copy)]
    union InputData {
        keyboard: KeybdInput,
    }

    #[repr(C)]
    #[derive(Clone, Copy)]
    struct Input {
        input_type: u32,
        data: InputData,
    }

    const INPUT_KEYBOARD: u32 = 1;
    const KEYEVENTF_KEYUP: u32 = 0x0002;
    const KEYEVENTF_UNICODE: u32 = 0x0004;

    #[link(name = "User32")]
    extern "system" {
        fn SendInput(input_count: u32, inputs: *const Input, input_size: i32) -> u32;
    }

    fn keyboard_input(virtual_key: u16, scan_code: u16, flags: u32) -> Input {
        Input {
            input_type: INPUT_KEYBOARD,
            data: InputData {
                keyboard: KeybdInput {
                    virtual_key,
                    scan_code,
                    flags,
                    time: 0,
                    extra_info: 0,
                },
            },
        }
    }

    fn send_inputs(inputs: &[Input]) -> bool {
        if inputs.is_empty() {
            return true;
        }
        let Ok(input_count) = u32::try_from(inputs.len()) else {
            return false;
        };
        // SAFETY: `inputs` contains repr(C) INPUT values which live through the
        // call. The size equals the ABI size expected by User32!SendInput.
        unsafe {
            SendInput(
                input_count,
                inputs.as_ptr(),
                std::mem::size_of::<Input>() as i32,
            ) == input_count
        }
    }

    pub fn inject_virtual_key(virtual_key: u16, pressed: bool) -> bool {
        let flags = if pressed { 0 } else { KEYEVENTF_KEYUP };
        send_inputs(&[keyboard_input(virtual_key, 0, flags)])
    }

    pub fn inject_text(text: &str) -> bool {
        let mut inputs = Vec::with_capacity(text.len().saturating_mul(2));
        for unit in text.encode_utf16() {
            inputs.push(keyboard_input(0, unit, KEYEVENTF_UNICODE));
            inputs.push(keyboard_input(0, unit, KEYEVENTF_UNICODE | KEYEVENTF_KEYUP));
        }
        send_inputs(&inputs)
    }
}

impl PlatformBridge for WindowsBridge {
    fn capabilities(&self) -> BridgeCapabilities {
        #[cfg(windows)]
        {
            return BridgeCapabilities {
                platform: Platform::Windows,
                input_injection: Capability::Available,
                input_source: Capability::ReadOnly,
                tray: Capability::Unsupported,
                visibility: Capability::Available,
                detail_code: "windows-sendinput-unicode-input-source-process-scope",
            };
        }
        #[cfg(not(windows))]
        {
            BridgeCapabilities::unsupported()
        }
    }

    fn inject_virtual_key(&self, virtual_key: u16, pressed: bool) -> Result<(), BridgeError> {
        #[cfg(windows)]
        {
            if native::inject_virtual_key(virtual_key, pressed) {
                return Ok(());
            }
            return Err(BridgeError::new(
                "input-injection-blocked",
                "SendInput inserted no event; UIPI or the target integrity level may block injection",
            ));
        }
        #[cfg(not(windows))]
        {
            let _ = (virtual_key, pressed);
            Err(BridgeError::new(
                "platform-unsupported",
                "the Windows bridge was called on a non-Windows host",
            ))
        }
    }

    fn inject_text(&self, text: &str) -> Result<(), BridgeError> {
        #[cfg(windows)]
        {
            if native::inject_text(text) {
                return Ok(());
            }
            return Err(BridgeError::new(
                "unicode-input-blocked",
                "SendInput could not insert the requested UTF-16 text; UIPI may block the target",
            ));
        }
        #[cfg(not(windows))]
        {
            let _ = text;
            Err(BridgeError::new(
                "platform-unsupported",
                "the Windows bridge was called on a non-Windows host",
            ))
        }
    }

    fn activate_next_input_source(&self) -> Result<(), BridgeError> {
        Err(BridgeError::new(
            "input-source-read-only",
            "Windows source switching remains process-scoped until the TSF focused-target adapter is implemented",
        ))
    }
}

#[cfg(test)]
mod tests {
    use super::WindowsBridge;
    #[cfg(windows)]
    use onboard_bridge_api::Capability;
    use onboard_bridge_api::{Platform, PlatformBridge};

    #[test]
    fn reports_the_host_specific_capability_boundary() {
        let capabilities = WindowsBridge::new().capabilities();
        #[cfg(windows)]
        {
            assert_eq!(Platform::Windows, capabilities.platform);
            assert_eq!(Capability::Available, capabilities.input_injection);
            assert_eq!(Capability::ReadOnly, capabilities.input_source);
            assert_eq!(Capability::Available, capabilities.visibility);
        }
        #[cfg(not(windows))]
        {
            assert_eq!(Platform::Unsupported, capabilities.platform);
        }
    }
}
