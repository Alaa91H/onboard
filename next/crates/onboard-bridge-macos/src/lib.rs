//! macOS bridge for the next independent Onboard application.
//!
//! Quartz keyboard events require user-granted Accessibility permission. The
//! bridge reports that permission boundary before attempting to post an event;
//! it never presents a denied permission as a successful key operation.

use onboard_bridge_api::{BridgeCapabilities, BridgeError, PlatformBridge};
#[cfg(target_os = "macos")]
use onboard_bridge_api::{Capability, Platform};

#[derive(Default)]
pub struct MacOsBridge;

impl MacOsBridge {
    pub const fn new() -> Self {
        Self
    }
}

#[cfg(target_os = "macos")]
mod native {
    use std::ffi::c_void;

    type CGEventRef = *mut c_void;
    const K_CG_HID_EVENT_TAP: u32 = 0;

    #[link(name = "ApplicationServices", kind = "framework")]
    extern "C" {
        fn AXIsProcessTrusted() -> u8;
        fn CGEventCreateKeyboardEvent(
            source: *const c_void,
            virtual_key: u16,
            key_down: u8,
        ) -> CGEventRef;
        fn CGEventPost(tap: u32, event: CGEventRef);
    }

    #[link(name = "CoreFoundation", kind = "framework")]
    extern "C" {
        fn CFRelease(value: *const c_void);
    }

    pub fn accessibility_trusted() -> bool {
        // SAFETY: AXIsProcessTrusted takes no arguments and has no ownership
        // transfer. Its Boolean return is represented as an unsigned byte.
        unsafe { AXIsProcessTrusted() != 0 }
    }

    pub fn inject_virtual_key(virtual_key: u16, pressed: bool) -> bool {
        let key_down = u8::from(pressed);
        // SAFETY: a null source is supported by Quartz and the returned event
        // is checked for null before being posted and released exactly once.
        let event = unsafe { CGEventCreateKeyboardEvent(std::ptr::null(), virtual_key, key_down) };
        if event.is_null() {
            return false;
        }
        // SAFETY: `event` is a valid CGEventRef returned above. CGEventPost
        // does not take ownership; CFRelease balances the create operation.
        unsafe {
            CGEventPost(K_CG_HID_EVENT_TAP, event);
            CFRelease(event.cast_const());
        }
        true
    }
}

impl PlatformBridge for MacOsBridge {
    fn capabilities(&self) -> BridgeCapabilities {
        #[cfg(target_os = "macos")]
        {
            let injection = if native::accessibility_trusted() {
                Capability::Available
            } else {
                Capability::PermissionRequired
            };
            return BridgeCapabilities {
                platform: Platform::MacOs,
                input_injection: injection,
                input_source: Capability::ReadOnly,
                tray: Capability::Unsupported,
                visibility: Capability::Unsupported,
                detail_code: "macos-quartz-accessibility-tis-pending",
            };
        }
        #[cfg(not(target_os = "macos"))]
        {
            BridgeCapabilities::unsupported()
        }
    }

    fn inject_virtual_key(&self, virtual_key: u16, pressed: bool) -> Result<(), BridgeError> {
        #[cfg(target_os = "macos")]
        {
            if !native::accessibility_trusted() {
                return Err(BridgeError::new(
                    "accessibility-permission-required",
                    "grant Accessibility permission to Onboard before keyboard events can be posted",
                ));
            }
            if native::inject_virtual_key(virtual_key, pressed) {
                return Ok(());
            }
            return Err(BridgeError::new(
                "event-creation-failed",
                "Quartz could not create a keyboard event",
            ));
        }
        #[cfg(not(target_os = "macos"))]
        {
            let _ = (virtual_key, pressed);
            Err(BridgeError::new(
                "platform-unsupported",
                "the macOS bridge was called on a non-macOS host",
            ))
        }
    }

    fn inject_text(&self, _text: &str) -> Result<(), BridgeError> {
        Err(BridgeError::new(
            "unicode-text-input-pending",
            "macOS Unicode text injection is pending the focused-target adapter",
        ))
    }

    fn activate_next_input_source(&self) -> Result<(), BridgeError> {
        Err(BridgeError::new(
            "input-source-read-only",
            "Text Input Services selection is pending; the current bridge reports capability without simulating shortcuts",
        ))
    }
}

#[cfg(test)]
mod tests {
    use super::MacOsBridge;
    #[cfg(target_os = "macos")]
    use onboard_bridge_api::Capability;
    use onboard_bridge_api::{Platform, PlatformBridge};

    #[test]
    fn reports_macos_permission_boundary_or_host_unsupported() {
        let capabilities = MacOsBridge::new().capabilities();
        #[cfg(target_os = "macos")]
        {
            assert_eq!(Platform::MacOs, capabilities.platform);
            assert_eq!(Capability::ReadOnly, capabilities.input_source);
            assert!(matches!(
                capabilities.input_injection,
                Capability::Available | Capability::PermissionRequired
            ));
        }
        #[cfg(not(target_os = "macos"))]
        {
            assert_eq!(Platform::Unsupported, capabilities.platform);
        }
    }
}
