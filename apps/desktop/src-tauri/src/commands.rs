//! IPC commands callable from the frontend.

use gc_core::{AppInfo, Probed};
use serde::Deserialize;
use tauri::{AppHandle, Manager};

#[tauri::command]
pub fn get_app_info(app: AppHandle) -> AppInfo {
    let log_dir = match app.path().app_log_dir() {
        Ok(path) => Probed::known(path.display().to_string()),
        Err(err) => Probed::unavailable(err.to_string()),
    };
    build_app_info(log_dir)
}

pub(crate) fn build_app_info(log_dir: Probed<String>) -> AppInfo {
    AppInfo {
        name: "GameCheck".into(),
        version: env!("CARGO_PKG_VERSION").into(),
        build_profile: if cfg!(debug_assertions) {
            "debug"
        } else {
            "release"
        }
        .into(),
        target_os: std::env::consts::OS.into(),
        target_arch: std::env::consts::ARCH.into(),
        log_dir,
    }
}

/// What the frontend reports once it has rendered its first screen.
#[derive(Debug, Clone, Deserialize, serde::Serialize)]
#[serde(rename_all = "camelCase")]
pub struct FrontendReady {
    pub language: String,
    pub direction: String,
    pub route: String,
    pub nav_items: u32,
}

/// Called once by the frontend after the first render. Used for logging and by the
/// smoke test that CI runs against the built executable.
#[tauri::command]
pub fn frontend_ready(app: AppHandle, report: FrontendReady) {
    log::info!(
        "frontend ready: language={} direction={} route={} nav_items={}",
        report.language,
        report.direction,
        report.route,
        report.nav_items
    );
    crate::smoke::on_frontend_ready(&app, &report);
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn app_info_reports_package_version() {
        let info = build_app_info(Probed::unavailable("test"));
        assert_eq!(info.version, env!("CARGO_PKG_VERSION"));
        assert_eq!(info.name, "GameCheck");
        assert_eq!(info.target_os, std::env::consts::OS);
    }

    #[test]
    fn frontend_ready_accepts_camel_case() {
        let report: FrontendReady =
            serde_json::from_str(r#"{"language":"ar","direction":"rtl","route":"/","navItems":7}"#)
                .unwrap();
        assert_eq!(report.nav_items, 7);
        assert_eq!(report.direction, "rtl");
    }
}
