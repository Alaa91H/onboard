//! Bootstrap executable for the independent Onboard application.
//!
//! It is intentionally a diagnostic command in this milestone. GTK4 presentation,
//! tray integration, and installers are added only after this platform contract
//! passes native compilation and capability tests on its target operating system.

use onboard_bridge_api::{BridgeCapabilities, PlatformBridge};
use onboard_bridge_macos::MacOsBridge;
use onboard_bridge_windows::WindowsBridge;
use onboard_core::{KeyboardState, TextDirection};

fn bridge() -> Box<dyn PlatformBridge> {
    #[cfg(windows)]
    {
        return Box::new(WindowsBridge::new());
    }
    #[cfg(target_os = "macos")]
    {
        return Box::new(MacOsBridge::new());
    }
    #[cfg(not(any(windows, target_os = "macos")))]
    {
        // Constructing both adapters on non-target hosts keeps their public
        // contracts compiled by the workspace tests without invoking platform FFI.
        let _ = (WindowsBridge::new(), MacOsBridge::new());
        Box::new(UnsupportedBridge)
    }
}

struct UnsupportedBridge;

impl PlatformBridge for UnsupportedBridge {
    fn capabilities(&self) -> BridgeCapabilities {
        BridgeCapabilities::unsupported()
    }

    fn inject_virtual_key(
        &self,
        _virtual_key: u16,
        _pressed: bool,
    ) -> Result<(), onboard_bridge_api::BridgeError> {
        Err(onboard_bridge_api::BridgeError::new(
            "platform-unsupported",
            "onboard-next bootstrap currently has native bridges only for Windows and macOS",
        ))
    }

    fn activate_next_input_source(&self) -> Result<(), onboard_bridge_api::BridgeError> {
        Err(onboard_bridge_api::BridgeError::new(
            "platform-unsupported",
            "input source selection needs a target platform bridge",
        ))
    }
}

fn direction_name(direction: TextDirection) -> &'static str {
    match direction {
        TextDirection::LeftToRight => "ltr",
        TextDirection::RightToLeft => "rtl",
    }
}

fn print_diagnostics(locale: &str) {
    let mut state = KeyboardState::default();
    state.set_locale(locale);
    let capabilities = bridge().capabilities();
    println!(
        concat!(
            "{{\"application\":\"onboard-next-bootstrap\",",
            "\"profile\":\"windows-compact\",",
            "\"locale\":\"{}\",",
            "\"direction\":\"{}\",",
            "\"bridge\":{}}}"
        ),
        locale,
        direction_name(state.direction),
        capabilities.as_json(),
    );
}

fn main() {
    let arguments: Vec<String> = std::env::args().collect();
    match arguments.get(1).map(String::as_str) {
        Some("diagnose") => {
            let locale = arguments.get(2).map(String::as_str).unwrap_or("en_US");
            print_diagnostics(locale);
        }
        Some("key") => {
            let Some(raw_key) = arguments.get(2) else {
                eprintln!("usage: onboard-next key <virtual-key>");
                std::process::exit(2);
            };
            let key = match raw_key.parse::<u16>() {
                Ok(key) => key,
                Err(_) => {
                    eprintln!("invalid virtual key: {raw_key}");
                    std::process::exit(2);
                }
            };
            let active_bridge = bridge();
            match active_bridge
                .inject_virtual_key(key, true)
                .and_then(|_| active_bridge.inject_virtual_key(key, false))
            {
                Ok(()) => println!("{{\"result\":\"ok\",\"virtual_key\":{key}}}"),
                Err(error) => {
                    eprintln!(
                        "{{\"result\":\"error\",\"code\":\"{}\",\"detail\":\"{}\"}}",
                        error.code, error.detail
                    );
                    std::process::exit(1);
                }
            }
        }
        Some("switch-source") => match bridge().activate_next_input_source() {
            Ok(()) => println!("{{\"result\":\"ok\"}}"),
            Err(error) => {
                eprintln!(
                    "{{\"result\":\"error\",\"code\":\"{}\",\"detail\":\"{}\"}}",
                    error.code, error.detail
                );
                std::process::exit(1);
            }
        },
        _ => {
            println!("onboard-next bootstrap\n\ncommands:\n  diagnose [locale]\n  key <virtual-key>\n  switch-source");
        }
    }
}
