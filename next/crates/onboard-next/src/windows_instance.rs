//! Windows single-instance ownership and shortcut activation.
//!
//! Start-menu and desktop shortcuts launch a process every time they are clicked.
//! The primary instance owns a named mutex; a later launch restores the existing
//! window and exits, preventing hidden duplicate keyboards in the tray.

use std::ffi::c_void;
use std::iter;

const ERROR_ALREADY_EXISTS: u32 = 183;
const SW_RESTORE: i32 = 9;
const APP_WINDOW_TITLE: &str = "Onboard Next";
const MUTEX_NAME: &str = "Local\\OnboardNext.SingleInstance.v1";

pub struct PrimaryInstance {
    handle: *mut c_void,
}

impl PrimaryInstance {
    pub fn acquire_or_show_existing() -> Result<Option<Self>, String> {
        let mutex_name = wide(MUTEX_NAME);
        // SAFETY: the NUL-terminated name remains alive for the call and the
        // returned handle is retained by the primary process until Drop.
        let handle = unsafe { CreateMutexW(std::ptr::null(), 0, mutex_name.as_ptr()) };
        if handle.is_null() {
            return Err("تعذر حجز مثيل التطبيق".to_owned());
        }
        // SAFETY: GetLastError reads the status established by CreateMutexW.
        if unsafe { GetLastError() } == ERROR_ALREADY_EXISTS {
            // SAFETY: the mutex handle is no longer required by this secondary
            // process and the title buffer is valid for FindWindowW.
            unsafe {
                let title = wide(APP_WINDOW_TITLE);
                let window = FindWindowW(std::ptr::null(), title.as_ptr());
                if !window.is_null() {
                    ShowWindow(window, SW_RESTORE);
                    SetForegroundWindow(window);
                }
                CloseHandle(handle);
            }
            return Ok(None);
        }
        Ok(Some(Self { handle }))
    }
}

impl Drop for PrimaryInstance {
    fn drop(&mut self) {
        // SAFETY: this handle was returned by CreateMutexW for the primary
        // process and is closed exactly once when that process exits.
        unsafe {
            CloseHandle(self.handle);
        }
    }
}

fn wide(value: &str) -> Vec<u16> {
    value.encode_utf16().chain(iter::once(0)).collect()
}

#[link(name = "Kernel32")]
extern "system" {
    fn CreateMutexW(attributes: *const c_void, initial_owner: i32, name: *const u16)
        -> *mut c_void;
    fn GetLastError() -> u32;
    fn CloseHandle(handle: *mut c_void) -> i32;
}

#[link(name = "User32")]
extern "system" {
    fn FindWindowW(class_name: *const u16, window_name: *const u16) -> *mut c_void;
    fn ShowWindow(window: *mut c_void, command: i32) -> i32;
    fn SetForegroundWindow(window: *mut c_void) -> i32;
}

#[cfg(test)]
mod tests {
    use super::{wide, APP_WINDOW_TITLE, MUTEX_NAME};

    #[test]
    fn win32_strings_are_nul_terminated() {
        assert_eq!(wide(APP_WINDOW_TITLE).last(), Some(&0));
        assert_eq!(wide(MUTEX_NAME).last(), Some(&0));
    }
}
