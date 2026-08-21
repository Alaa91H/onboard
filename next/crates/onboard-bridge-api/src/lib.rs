//! Platform-neutral bridge contract for the independent Onboard application.

use std::fmt;

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Platform {
    Linux,
    Windows,
    MacOs,
    Unsupported,
}

impl Platform {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Linux => "linux",
            Self::Windows => "windows",
            Self::MacOs => "macos",
            Self::Unsupported => "unsupported",
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum Capability {
    Available,
    PermissionRequired,
    ReadOnly,
    Unsupported,
}

impl Capability {
    pub const fn as_str(self) -> &'static str {
        match self {
            Self::Available => "available",
            Self::PermissionRequired => "permission-required",
            Self::ReadOnly => "read-only",
            Self::Unsupported => "unsupported",
        }
    }
}

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub struct BridgeCapabilities {
    pub platform: Platform,
    pub input_injection: Capability,
    pub input_source: Capability,
    pub tray: Capability,
    pub visibility: Capability,
    pub detail_code: &'static str,
}

impl BridgeCapabilities {
    pub const fn unsupported() -> Self {
        Self {
            platform: Platform::Unsupported,
            input_injection: Capability::Unsupported,
            input_source: Capability::Unsupported,
            tray: Capability::Unsupported,
            visibility: Capability::Unsupported,
            detail_code: "platform-unsupported",
        }
    }

    /// JSON generated without a serializer so the bootstrap binary has no
    /// third-party dependency before the offline-vendoring policy is expanded.
    pub fn as_json(self) -> String {
        format!(
            concat!(
                "{{\"platform\":\"{}\",",
                "\"input_injection\":\"{}\",",
                "\"input_source\":\"{}\",",
                "\"tray\":\"{}\",",
                "\"visibility\":\"{}\",",
                "\"detail_code\":\"{}\"}}"
            ),
            self.platform.as_str(),
            self.input_injection.as_str(),
            self.input_source.as_str(),
            self.tray.as_str(),
            self.visibility.as_str(),
            self.detail_code,
        )
    }
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct BridgeError {
    pub code: &'static str,
    pub detail: &'static str,
}

impl BridgeError {
    pub const fn new(code: &'static str, detail: &'static str) -> Self {
        Self { code, detail }
    }
}

impl fmt::Display for BridgeError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(formatter, "{}: {}", self.code, self.detail)
    }
}

impl std::error::Error for BridgeError {}

pub trait PlatformBridge {
    fn capabilities(&self) -> BridgeCapabilities;
    fn inject_virtual_key(&self, virtual_key: u16, pressed: bool) -> Result<(), BridgeError>;
    fn inject_text(&self, text: &str) -> Result<(), BridgeError>;
    fn activate_next_input_source(&self) -> Result<(), BridgeError>;
}

#[cfg(test)]
mod tests {
    use super::{BridgeCapabilities, Capability, Platform};

    #[test]
    fn capabilities_serialize_stable_machine_codes() {
        let capabilities = BridgeCapabilities {
            platform: Platform::Windows,
            input_injection: Capability::Available,
            input_source: Capability::ReadOnly,
            tray: Capability::Available,
            visibility: Capability::Available,
            detail_code: "windows-sendinput-ready",
        };
        assert_eq!(
            "{\"platform\":\"windows\",\"input_injection\":\"available\",\"input_source\":\"read-only\",\"tray\":\"available\",\"visibility\":\"available\",\"detail_code\":\"windows-sendinput-ready\"}",
            capabilities.as_json()
        );
    }
}
