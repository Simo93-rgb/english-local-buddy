// English Buddy – Tauri Application Library
//
// This module contains the Tauri builder setup, window management,
// and system-level configuration for the desktop application.

use tauri::Manager;

/// Tauri command stub: greet the user (can be called from the frontend).
#[tauri::command]
fn greet(name: &str) -> String {
    format!("Hello, {}! Welcome to English Buddy.", name)
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            // ------------------------------------------------------------------
            // Logging (debug builds only)
            // ------------------------------------------------------------------
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }

            // ------------------------------------------------------------------
            // Window configuration
            // ------------------------------------------------------------------
            if let Some(window) = app.get_webview_window("main") {
                // Set a reasonable minimum window size for the UI
                let _ = window.set_min_size(Some(tauri::LogicalSize::new(640.0, 480.0)));

                log::info!("Main window initialised");
            }

            // ------------------------------------------------------------------
            // Microphone permissions
            // ------------------------------------------------------------------
            // On Linux (WebKitGTK), microphone access is handled by the browser
            // engine and the OS-level PipeWire / PulseAudio permissions.
            // No explicit Tauri API call is needed.
            //
            // On macOS, the Info.plist must include NSMicrophoneUsageDescription.
            // On Windows, the user is prompted by the OS automatically.
            //
            // TODO: If targeting mobile (Android/iOS), use tauri-plugin-permissions
            //       to request microphone access at runtime:
            //       app.handle().plugin(tauri_plugin_permissions::init())?;

            log::info!("English Buddy application started successfully");

            Ok(())
        })
        .invoke_handler(tauri::generate_handler![greet])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
