//! GameCheck desktop application: Tauri setup, plugins and IPC commands.

mod commands;
mod smoke;

use tauri::Manager;
use tauri_plugin_log::{RotationStrategy, Target, TargetKind};

/// Log files larger than this are rotated.
const MAX_LOG_FILE_BYTES: u128 = 2 * 1024 * 1024;

pub fn run() {
    let log_plugin = tauri_plugin_log::Builder::new()
        .targets([
            Target::new(TargetKind::Stdout),
            Target::new(TargetKind::LogDir {
                file_name: Some("gamecheck".into()),
            }),
        ])
        .level(if cfg!(debug_assertions) {
            log::LevelFilter::Debug
        } else {
            log::LevelFilter::Info
        })
        .max_file_size(MAX_LOG_FILE_BYTES)
        .rotation_strategy(RotationStrategy::KeepSome(5))
        .build();

    let result = tauri::Builder::default()
        // Must be registered first: a second launch focuses the running window and exits.
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.unminimize();
                let _ = window.set_focus();
            }
        }))
        .plugin(log_plugin)
        .setup(|app| {
            install_panic_logger();
            log::info!(
                "GameCheck {} starting ({} {}, {})",
                env!("CARGO_PKG_VERSION"),
                std::env::consts::OS,
                std::env::consts::ARCH,
                if cfg!(debug_assertions) {
                    "debug"
                } else {
                    "release"
                }
            );
            smoke::start_watchdog_if_enabled(app.handle());
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::get_app_info,
            commands::frontend_ready
        ])
        .run(tauri::generate_context!());

    if let Err(err) = result {
        log::error!("GameCheck failed to start: {err}");
        eprintln!("GameCheck failed to start: {err}");
        std::process::exit(1);
    }
}

/// Send panics to the log file as well as stderr, so crashes can be diagnosed.
fn install_panic_logger() {
    let default_hook = std::panic::take_hook();
    std::panic::set_hook(Box::new(move |info| {
        log::error!("panic: {info}");
        default_hook(info);
    }));
}
