//! Smoke test mode, used by CI to prove that the built executable really starts,
//! loads its interface in the system WebView and can talk to Rust over IPC.
//!
//! Enabled only when `GAMECHECK_SMOKE_TEST=1`. The app then exits with code 0 as soon
//! as the frontend reports that it rendered, or with code 2 if that does not happen
//! within the timeout. When `GAMECHECK_SMOKE_OUT` is set, the frontend's report is
//! written there as JSON. Normal launches are not affected.

use std::time::Duration;

use tauri::AppHandle;

use crate::commands::FrontendReady;

const TIMEOUT: Duration = Duration::from_secs(90);

fn enabled() -> bool {
    std::env::var("GAMECHECK_SMOKE_TEST").is_ok_and(|v| v == "1")
}

pub fn start_watchdog_if_enabled(app: &AppHandle) {
    if !enabled() {
        return;
    }
    log::info!(
        "smoke test mode: waiting up to {}s for the frontend",
        TIMEOUT.as_secs()
    );
    let app = app.clone();
    std::thread::spawn(move || {
        std::thread::sleep(TIMEOUT);
        log::error!("smoke test failed: frontend did not report ready in time");
        app.exit(2);
    });
}

pub fn on_frontend_ready(app: &AppHandle, report: &FrontendReady) {
    if !enabled() {
        return;
    }
    if let Ok(path) = std::env::var("GAMECHECK_SMOKE_OUT") {
        match serde_json::to_string_pretty(report) {
            Ok(json) => {
                if let Err(err) = std::fs::write(&path, json) {
                    log::error!("smoke test: could not write {path}: {err}");
                    app.exit(3);
                    return;
                }
            }
            Err(err) => {
                log::error!("smoke test: could not serialise report: {err}");
                app.exit(3);
                return;
            }
        }
    }
    log::info!("smoke test passed");
    app.exit(0);
}
