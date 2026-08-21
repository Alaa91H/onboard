//! Windows System Tray integration for Onboard Next.
//!
//! The tray object is deliberately owned by the application state: dropping it
//! removes the icon from Windows, while keeping it alive lets users restore the
//! compact keyboard after the primary window is hidden.

use tray_icon::{
    menu::{Menu, MenuEvent, MenuItem},
    Icon, MouseButton, MouseButtonState, TrayIcon, TrayIconBuilder, TrayIconEvent,
};

const SHOW_MENU_ID: &str = "onboard-next.show";
const HIDE_MENU_ID: &str = "onboard-next.hide";
const EXIT_MENU_ID: &str = "onboard-next.exit";

#[derive(Clone, Copy, Debug, Eq, PartialEq)]
pub enum TrayAction {
    Show,
    Hide,
    Toggle,
    Exit,
}

pub struct SystemTray {
    _icon: TrayIcon,
}

impl SystemTray {
    pub fn create() -> Result<Self, String> {
        let menu = Menu::new();
        let show = MenuItem::with_id(SHOW_MENU_ID, "إظهار اللوحة", true, None);
        let hide = MenuItem::with_id(HIDE_MENU_ID, "إخفاء إلى منطقة الإعلام", true, None);
        let exit = MenuItem::with_id(EXIT_MENU_ID, "إنهاء Onboard Next", true, None);
        menu.append_items(&[&show, &hide, &exit])
            .map_err(|error| format!("could not create tray menu: {error}"))?;

        let icon = TrayIconBuilder::new()
            .with_id("onboard-next")
            .with_menu(Box::new(menu))
            .with_menu_on_left_click(false)
            .with_tooltip("Onboard Next — لوحة مفاتيح على الشاشة")
            .with_icon(keyboard_icon()?)
            .build()
            .map_err(|error| format!("could not create tray icon: {error}"))?;
        Ok(Self { _icon: icon })
    }

    pub fn next_action(&self) -> Option<TrayAction> {
        let mut action = None;
        while let Ok(event) = MenuEvent::receiver().try_recv() {
            action = match event.id.as_ref() {
                SHOW_MENU_ID => Some(TrayAction::Show),
                HIDE_MENU_ID => Some(TrayAction::Hide),
                EXIT_MENU_ID => Some(TrayAction::Exit),
                _ => action,
            };
        }

        while let Ok(event) = TrayIconEvent::receiver().try_recv() {
            if matches!(
                event,
                TrayIconEvent::Click {
                    button: MouseButton::Left,
                    button_state: MouseButtonState::Up,
                    ..
                }
            ) {
                action = Some(TrayAction::Toggle);
            }
        }
        action
    }
}

fn keyboard_icon() -> Result<Icon, String> {
    const SIZE: u32 = 32;
    let mut rgba = vec![0_u8; (SIZE * SIZE * 4) as usize];
    for y in 0..SIZE {
        for x in 0..SIZE {
            let offset = ((y * SIZE + x) * 4) as usize;
            let inside_keyboard = (3..29).contains(&x) && (7..26).contains(&y);
            let key = inside_keyboard
                && (5..27).contains(&x)
                && (9..26).contains(&y)
                && ((x - 5) % 6 < 4)
                && ((y - 9) % 6 < 4)
                && !(y > 20 && !(8..24).contains(&x));
            let color = if key {
                [245, 248, 255, 255]
            } else if inside_keyboard {
                [37, 99, 235, 255]
            } else {
                [0, 0, 0, 0]
            };
            rgba[offset..offset + 4].copy_from_slice(&color);
        }
    }
    Icon::from_rgba(rgba, SIZE, SIZE).map_err(|error| format!("invalid tray icon: {error}"))
}

#[cfg(test)]
mod tests {
    use super::{keyboard_icon, TrayAction};

    #[test]
    fn keyboard_icon_is_valid_rgba() {
        assert!(keyboard_icon().is_ok());
    }

    #[test]
    fn tray_actions_cover_visibility_and_exit() {
        assert_ne!(TrayAction::Show, TrayAction::Hide);
        assert_ne!(TrayAction::Toggle, TrayAction::Exit);
    }
}
