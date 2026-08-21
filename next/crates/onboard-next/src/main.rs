//! Native desktop entry point for the independent Onboard application.
//!
//! The application deliberately keeps rendering and state local. Text injection
//! is delegated to a narrowly scoped platform bridge so the compact on-screen
//! keyboard can remain responsive while preserving a testable capability boundary.

#![cfg_attr(windows, windows_subsystem = "windows")]

#[cfg(any(windows, target_os = "macos"))]
use eframe::egui;
use onboard_bridge_api::{BridgeCapabilities, PlatformBridge};
use onboard_bridge_macos::MacOsBridge;
use onboard_bridge_windows::WindowsBridge;
use onboard_core::{KeyboardState, TextDirection};

#[cfg(windows)]
mod windows_instance;
#[cfg(windows)]
mod windows_tray;
#[cfg(windows)]
mod windows_update;

#[cfg(any(windows, target_os = "macos"))]
const APP_ID: &str = "org.onboard.OnboardNext";
#[cfg(any(windows, target_os = "macos"))]
const LAYOUT_STORAGE_KEY: &str = "onboard-next.layout";
#[cfg(windows)]
const UPDATE_LAST_CHECKED_STORAGE_KEY: &str = "onboard-next.update-last-checked";
#[cfg(windows)]
const START_MINIMIZED_ARGUMENT: &str = "--start-minimized";
#[cfg(any(windows, target_os = "macos"))]
const ENGLISH_ROWS: &[&[&str]] = &[
    &["q", "w", "e", "r", "t", "y", "u", "i", "o", "p"],
    &["a", "s", "d", "f", "g", "h", "j", "k", "l"],
    &["z", "x", "c", "v", "b", "n", "m"],
];
#[cfg(any(windows, target_os = "macos"))]
const ARABIC_ROWS: &[&[&str]] = &[
    &["ض", "ص", "ث", "ق", "ف", "غ", "ع", "ه", "خ", "ح"],
    &["ش", "س", "ي", "ب", "ل", "ا", "ت", "ن", "م", "ك"],
    &["ئ", "ء", "ؤ", "ر", "لا", "ى", "ة", "و", "ز", "ظ"],
];
#[cfg(any(windows, target_os = "macos"))]
const EMOJI: &[&str] = &["😀", "😁", "😂", "😊", "😍", "👍", "❤️", "🎉", "✅", "🙏"];

#[cfg(any(windows, target_os = "macos"))]
#[derive(Clone, Copy, Debug, Eq, PartialEq)]
enum KeyboardLayout {
    English,
    Arabic,
}

#[cfg(any(windows, target_os = "macos"))]
impl KeyboardLayout {
    fn from_storage(value: Option<String>) -> Self {
        match value.as_deref() {
            Some("ar") => Self::Arabic,
            _ => Self::English,
        }
    }

    const fn locale(self) -> &'static str {
        match self {
            Self::English => "en_US",
            Self::Arabic => "ar_SA",
        }
    }

    const fn language_button_label(self) -> &'static str {
        match self {
            Self::English => "العربية",
            Self::Arabic => "English",
        }
    }

    const fn storage_value(self) -> &'static str {
        match self {
            Self::English => "en",
            Self::Arabic => "ar",
        }
    }

    const fn rows(self) -> &'static [&'static [&'static str]] {
        match self {
            Self::English => ENGLISH_ROWS,
            Self::Arabic => ARABIC_ROWS,
        }
    }

    fn toggle(&mut self) {
        *self = match self {
            Self::English => Self::Arabic,
            Self::Arabic => Self::English,
        };
    }
}

#[cfg(any(windows, target_os = "macos"))]
struct OnboardApp {
    bridge: Box<dyn PlatformBridge>,
    keyboard_state: KeyboardState,
    layout: KeyboardLayout,
    show_clipboard: bool,
    show_emoji: bool,
    clipboard_text: String,
    status: String,
    non_activating_window_configured: bool,
    #[cfg(windows)]
    system_tray: Option<windows_tray::SystemTray>,
    #[cfg(windows)]
    window_visible: bool,
    #[cfg(windows)]
    allow_exit: bool,
    #[cfg(windows)]
    update_status: windows_update::UpdateStatus,
    #[cfg(windows)]
    update_check: Option<windows_update::UpdateCheck>,
    #[cfg(windows)]
    last_update_check: Option<u64>,
}

#[cfg(any(windows, target_os = "macos"))]
impl OnboardApp {
    fn new(creation_context: &eframe::CreationContext<'_>) -> Self {
        configure_fonts(&creation_context.egui_ctx);
        let layout = KeyboardLayout::from_storage(
            creation_context
                .storage
                .and_then(|storage| storage.get_string(LAYOUT_STORAGE_KEY)),
        );
        let mut keyboard_state = KeyboardState::default();
        keyboard_state.set_locale(layout.locale());
        #[cfg(windows)]
        let (system_tray, status) = match windows_tray::SystemTray::create() {
            Ok(tray) => (Some(tray), "جاهز للكتابة في التطبيق النشط".to_owned()),
            Err(error) => (None, format!("تعذر إنشاء أيقونة منطقة الإعلام: {error}")),
        };
        #[cfg(windows)]
        let last_update_check = creation_context.storage.and_then(|storage| {
            storage
                .get_string(UPDATE_LAST_CHECKED_STORAGE_KEY)
                .and_then(|value| value.parse::<u64>().ok())
        });
        #[cfg(windows)]
        let (update_status, update_check) =
            if windows_update::should_check(last_update_check, std::time::SystemTime::now()) {
                (
                    windows_update::UpdateStatus::Checking,
                    Some(windows_update::start_background_check(
                        env!("CARGO_PKG_VERSION").to_owned(),
                        windows_architecture(),
                    )),
                )
            } else {
                (windows_update::UpdateStatus::Idle, None)
            };
        #[cfg(not(windows))]
        let status = "جاهز للكتابة في التطبيق النشط".to_owned();

        Self {
            bridge: bridge(),
            keyboard_state,
            layout,
            show_clipboard: false,
            show_emoji: false,
            clipboard_text: String::new(),
            status,
            non_activating_window_configured: false,
            #[cfg(windows)]
            system_tray,
            #[cfg(windows)]
            window_visible: !started_minimized(),
            #[cfg(windows)]
            allow_exit: false,
            #[cfg(windows)]
            update_status,
            #[cfg(windows)]
            update_check,
            #[cfg(windows)]
            last_update_check,
        }
    }

    fn select_layout(&mut self, layout: KeyboardLayout) {
        self.layout = layout;
        self.keyboard_state.set_locale(layout.locale());
        self.status = match layout {
            KeyboardLayout::English => "لوحة English جاهزة".to_owned(),
            KeyboardLayout::Arabic => "لوحة العربية جاهزة".to_owned(),
        };
    }

    fn inject_text(&mut self, text: &str) {
        if text.is_empty() {
            return;
        }
        match self.bridge.inject_text(text) {
            Ok(()) => {
                self.clipboard_text.push_str(text);
                self.status = format!("تم إدخال {text}");
            }
            Err(error) => self.status = format!("تعذر الإدخال: {error}"),
        }
    }

    fn inject_virtual_key(&mut self, virtual_key: u16) {
        let result = self
            .bridge
            .inject_virtual_key(virtual_key, true)
            .and_then(|_| self.bridge.inject_virtual_key(virtual_key, false));
        self.status = match result {
            Ok(()) => "تم إرسال المفتاح".to_owned(),
            Err(error) => format!("تعذر إرسال المفتاح: {error}"),
        };
    }

    #[cfg(windows)]
    fn show_window_from_tray(&mut self, context: &egui::Context) {
        self.window_visible = true;
        context.send_viewport_cmd(egui::ViewportCommand::Visible(true));
        context.send_viewport_cmd(egui::ViewportCommand::Minimized(false));
        self.status = "تم إظهار اللوحة من منطقة الإعلام".to_owned();
    }

    #[cfg(windows)]
    fn hide_window_to_tray(&mut self, context: &egui::Context) {
        self.window_visible = false;
        context.send_viewport_cmd(egui::ViewportCommand::Visible(false));
        self.status = "التطبيق يعمل في منطقة الإعلام".to_owned();
    }

    #[cfg(windows)]
    fn begin_update_check(&mut self) {
        if self.update_check.is_some() {
            return;
        }
        self.update_status = windows_update::UpdateStatus::Checking;
        self.update_check = Some(windows_update::start_background_check(
            env!("CARGO_PKG_VERSION").to_owned(),
            windows_architecture(),
        ));
    }

    #[cfg(windows)]
    fn poll_update_check(&mut self) {
        let status = self
            .update_check
            .as_ref()
            .and_then(windows_update::UpdateCheck::try_receive);
        if let Some(status) = status {
            self.update_check = None;
            self.last_update_check =
                Some(windows_update::unix_seconds(std::time::SystemTime::now()));
            self.update_status = status;
        }
    }

    #[cfg(windows)]
    fn show_update_status(&mut self, ui: &mut egui::Ui) {
        use egui::{Color32, Hyperlink, RichText};
        use windows_update::UpdateStatus;

        match self.update_status.clone() {
            UpdateStatus::Idle => {
                if ui.small_button("فحص التحديثات").clicked() {
                    self.begin_update_check();
                }
            }
            UpdateStatus::Checking => {
                ui.spinner();
                ui.weak("يجري فحص إصدار موثوق…");
            }
            UpdateStatus::UpToDate => {
                ui.colored_label(
                    Color32::from_rgb(22, 163, 74),
                    "أنت تستخدم أحدث إصدار منشور",
                );
                if ui.small_button("فحص مجدداً").clicked() {
                    self.begin_update_check();
                }
            }
            UpdateStatus::Available(offer) => {
                ui.colored_label(
                    Color32::from_rgb(37, 99, 235),
                    RichText::new(format!("إصدار {} متاح", offer.version)).strong(),
                );
                ui.add(Hyperlink::from_label_and_url(
                    "عرض الإصدار",
                    offer.release_url,
                ));
                if offer.installer_url.is_some() && offer.installer_sha256.is_some() {
                    ui.weak("سيصبح التثبيت من التطبيق متاحاً بعد توقيع الإصدار المستقر.");
                } else {
                    ui.weak("لا يوفّر الإصدار ملف تثبيت موثقاً لهذه المعمارية.");
                }
            }
            UpdateStatus::NoPublishedRelease => {
                ui.weak("لا يوجد إصدار مستقر منشور بعد.");
            }
            UpdateStatus::Unavailable(error) => {
                ui.colored_label(Color32::from_rgb(180, 83, 9), error);
                if ui.small_button("إعادة المحاولة").clicked() {
                    self.begin_update_check();
                }
            }
        }
    }

    #[cfg(windows)]
    fn process_system_tray(&mut self, context: &egui::Context) {
        use windows_tray::TrayAction;

        let action = self
            .system_tray
            .as_ref()
            .and_then(windows_tray::SystemTray::next_action);
        match action {
            Some(TrayAction::Show) => self.show_window_from_tray(context),
            Some(TrayAction::Hide) => self.hide_window_to_tray(context),
            Some(TrayAction::Toggle) if self.window_visible => self.hide_window_to_tray(context),
            Some(TrayAction::Toggle) => self.show_window_from_tray(context),
            Some(TrayAction::Exit) => {
                self.allow_exit = true;
                context.send_viewport_cmd(egui::ViewportCommand::Close);
            }
            None => {}
        }
    }

    fn compact_button(ui: &mut egui::Ui, label: &str) -> egui::Response {
        ui.add_sized([58.0, 42.0], egui::Button::new(label))
    }

    fn show_key_rows(&mut self, ui: &mut egui::Ui) {
        let layout = self.layout;
        for row in layout.rows() {
            ui.horizontal_centered(|ui| {
                let direction = match layout {
                    KeyboardLayout::English => egui::Layout::left_to_right(egui::Align::Center),
                    KeyboardLayout::Arabic => egui::Layout::right_to_left(egui::Align::Center),
                };
                ui.with_layout(direction, |ui| {
                    for key in *row {
                        if Self::compact_button(ui, key).clicked() {
                            self.inject_text(key);
                        }
                    }
                });
            });
        }
    }

    fn show_emoji_panel(&mut self, ui: &mut egui::Ui) {
        if !self.show_emoji {
            return;
        }
        ui.separator();
        ui.horizontal_wrapped(|ui| {
            for emoji in EMOJI {
                if ui
                    .add_sized([48.0, 40.0], egui::Button::new(*emoji))
                    .clicked()
                {
                    self.inject_text(emoji);
                }
            }
        });
    }

    fn show_clipboard_panel(&mut self, ui: &mut egui::Ui) {
        if !self.show_clipboard {
            return;
        }
        ui.separator();
        ui.horizontal(|ui| {
            ui.label("حافظة الجلسة:");
            if self.clipboard_text.is_empty() {
                ui.weak("لا توجد كتابة بعد");
            } else if ui.button("نسخ").clicked() {
                ui.output_mut(|output| output.copied_text = self.clipboard_text.clone());
                self.status = "تم نسخ محتوى حافظة الجلسة".to_owned();
            }
            if ui.button("مسح").clicked() {
                self.clipboard_text.clear();
                self.status = "تم مسح حافظة الجلسة".to_owned();
            }
        });
        if !self.clipboard_text.is_empty() {
            ui.label(&self.clipboard_text);
        }
    }
}

#[cfg(any(windows, target_os = "macos"))]
impl eframe::App for OnboardApp {
    fn update(&mut self, context: &egui::Context, frame: &mut eframe::Frame) {
        #[cfg(windows)]
        if !self.non_activating_window_configured {
            self.non_activating_window_configured = configure_non_activating_window(frame);
            if self.non_activating_window_configured {
                self.status = "جاهز للكتابة في التطبيق النشط".to_owned();
            }
        }
        #[cfg(windows)]
        {
            self.process_system_tray(context);
            self.poll_update_check();
            if context.input(|input| input.viewport().close_requested()) && !self.allow_exit {
                context.send_viewport_cmd(egui::ViewportCommand::CancelClose);
                self.hide_window_to_tray(context);
            }
            if self.window_visible
                && context.input(|input| input.viewport().minimized == Some(true))
            {
                self.hide_window_to_tray(context);
            }
            if self.system_tray.is_some() {
                context.request_repaint_after(std::time::Duration::from_millis(100));
            }
        }

        egui::CentralPanel::default().show(context, |ui| {
            ui.vertical(|ui| {
                egui::Frame::none()
                    .fill(egui::Color32::from_rgb(239, 246, 255))
                    .rounding(egui::Rounding::same(12.0))
                    .inner_margin(egui::Margin::symmetric(14.0, 10.0))
                    .show(ui, |ui| {
                        ui.horizontal(|ui| {
                            ui.vertical(|ui| {
                                ui.label(
                                    egui::RichText::new("ONBOARD NEXT")
                                        .size(11.0)
                                        .color(egui::Color32::from_rgb(37, 99, 235))
                                        .strong(),
                                );
                                ui.heading("لوحة مفاتيح سريعة");
                            });
                            ui.separator();
                            if ui.button(self.layout.language_button_label()).clicked() {
                                let next = match self.layout {
                                    KeyboardLayout::English => KeyboardLayout::Arabic,
                                    KeyboardLayout::Arabic => KeyboardLayout::English,
                                };
                                self.select_layout(next);
                            }
                            if ui
                                .selectable_label(self.show_clipboard, "الحافظة")
                                .clicked()
                            {
                                self.show_clipboard = !self.show_clipboard;
                            }
                            if ui.selectable_label(self.show_emoji, "الإيموجي").clicked() {
                                self.show_emoji = !self.show_emoji;
                            }
                            #[cfg(windows)]
                            if ui.button("إخفاء إلى الأيقونة").clicked() {
                                self.hide_window_to_tray(context);
                            }
                        });
                        #[cfg(windows)]
                        self.show_update_status(ui);
                    });

                ui.add_space(6.0);
                self.show_clipboard_panel(ui);
                self.show_emoji_panel(ui);
                self.show_key_rows(ui);

                ui.horizontal_centered(|ui| {
                    if ui.add_sized([90.0, 42.0], egui::Button::new("⌫")).clicked() {
                        self.inject_virtual_key(0x08);
                    }
                    if ui
                        .add_sized([300.0, 42.0], egui::Button::new("مسافة"))
                        .clicked()
                    {
                        self.inject_text(" ");
                    }
                    if ui.add_sized([90.0, 42.0], egui::Button::new("↵")).clicked() {
                        self.inject_virtual_key(0x0D);
                    }
                });

                ui.separator();
                ui.weak(&self.status);
            });
        });
    }

    fn save(&mut self, storage: &mut dyn eframe::Storage) {
        storage.set_string(LAYOUT_STORAGE_KEY, self.layout.storage_value().to_owned());
        #[cfg(windows)]
        if let Some(last_update_check) = self.last_update_check {
            storage.set_string(
                UPDATE_LAST_CHECKED_STORAGE_KEY,
                last_update_check.to_string(),
            );
        }
        storage.flush();
    }
}

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
            "onboard-next currently has native input bridges only for Windows and macOS",
        ))
    }

    fn inject_text(&self, _text: &str) -> Result<(), onboard_bridge_api::BridgeError> {
        Err(onboard_bridge_api::BridgeError::new(
            "platform-unsupported",
            "Unicode text injection needs a target platform bridge",
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
            "{{\"application\":\"onboard-next\",",
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

#[cfg(any(windows, target_os = "macos"))]
fn configure_fonts(context: &egui::Context) {
    let mut fonts = egui::FontDefinitions::default();
    fonts.font_data.insert(
        "onboard-noto-arabic".to_owned(),
        egui::FontData::from_static(include_bytes!(
            "../assets/fonts/NotoSansArabic-Variable.ttf"
        )),
    );
    for family in [egui::FontFamily::Proportional, egui::FontFamily::Monospace] {
        fonts
            .families
            .entry(family)
            .or_default()
            .insert(0, "onboard-noto-arabic".to_owned());
    }
    context.set_fonts(fonts);
}

#[cfg(windows)]
fn configure_non_activating_window(frame: &eframe::Frame) -> bool {
    use raw_window_handle::{HasWindowHandle, RawWindowHandle};
    use std::ffi::c_void;

    #[link(name = "User32")]
    extern "system" {
        fn GetWindowLongPtrW(window: *mut c_void, index: i32) -> isize;
        fn SetWindowLongPtrW(window: *mut c_void, index: i32, value: isize) -> isize;
    }

    const GWL_EXSTYLE: i32 = -20;
    const WS_EX_NOACTIVATE: isize = 0x0800_0000;

    let Ok(window_handle) = frame.window_handle() else {
        return false;
    };
    let RawWindowHandle::Win32(handle) = window_handle.as_raw() else {
        return false;
    };
    // SAFETY: eframe owns a valid Win32 HWND for the duration of the frame. The
    // style update only adds WS_EX_NOACTIVATE, so a button click preserves the
    // foreground text target instead of activating the keyboard window.
    unsafe {
        let window = handle.hwnd.get() as *mut c_void;
        let style = GetWindowLongPtrW(window, GWL_EXSTYLE);
        SetWindowLongPtrW(window, GWL_EXSTYLE, style | WS_EX_NOACTIVATE);
    }
    true
}

#[cfg(windows)]
fn started_minimized() -> bool {
    std::env::args().any(|argument| argument == START_MINIMIZED_ARGUMENT)
}

#[cfg(windows)]
fn windows_architecture() -> &'static str {
    if cfg!(target_arch = "aarch64") {
        "arm64"
    } else {
        "x64"
    }
}

#[cfg(any(windows, target_os = "macos"))]
fn run_app(start_minimized: bool) -> eframe::Result<()> {
    let native_options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default()
            .with_title("Onboard Next")
            .with_app_id(APP_ID)
            .with_inner_size([740.0, 450.0])
            .with_min_inner_size([620.0, 390.0])
            .with_max_inner_size([900.0, 560.0])
            .with_resizable(true)
            .with_active(false)
            .with_always_on_top()
            .with_visible(!start_minimized),
        persist_window: true,
        ..Default::default()
    };
    eframe::run_native(
        "Onboard Next",
        native_options,
        Box::new(|creation_context| Box::new(OnboardApp::new(creation_context))),
    )
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
        Some("--help") | Some("help") => {
            println!("Onboard Next\n\ncommands:\n  diagnose [locale]\n  key <virtual-key>\n  switch-source");
        }
        _ => {
            #[cfg(windows)]
            {
                let _primary_instance =
                    match windows_instance::PrimaryInstance::acquire_or_show_existing() {
                        Ok(Some(instance)) => instance,
                        Ok(None) => return,
                        Err(error) => {
                            eprintln!(
                                "Onboard Next could not reserve its primary instance: {error}"
                            );
                            std::process::exit(1);
                        }
                    };
                if let Err(error) = run_app(started_minimized()) {
                    eprintln!("Onboard Next could not start: {error}");
                    std::process::exit(1);
                }
            }
            #[cfg(target_os = "macos")]
            if let Err(error) = run_app(false) {
                eprintln!("Onboard Next could not start: {error}");
                std::process::exit(1);
            }
            #[cfg(not(any(windows, target_os = "macos")))]
            {
                eprintln!(
                    "Onboard Next desktop UI is currently available on Windows and macOS only."
                );
                std::process::exit(2);
            }
        }
    }
}
