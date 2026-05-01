// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

/// Desktop entry point for English Buddy.
///
/// Delegates to `app_lib::run()` which contains the full Tauri builder
/// configuration, plugin registration, and window management.
fn main() {
    app_lib::run();
}
