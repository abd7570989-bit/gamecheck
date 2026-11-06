//! Shared domain types used by every GameCheck crate.
//!
//! The central rule of GameCheck is that a value we could not read is reported as
//! unavailable, together with the reason, instead of being replaced by a default.
//! [`Probed`] encodes that rule in the type system.

use serde::{Deserialize, Serialize};

/// A value read from the system or from an external source.
///
/// Serialises as `{"status":"known","value":…}` or
/// `{"status":"unavailable","reason":"…"}` so the UI can tell the two apart.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(tag = "status", rename_all = "snake_case")]
pub enum Probed<T> {
    Known { value: T },
    Unavailable { reason: String },
}

impl<T> Probed<T> {
    pub fn known(value: T) -> Self {
        Probed::Known { value }
    }

    pub fn unavailable(reason: impl Into<String>) -> Self {
        Probed::Unavailable {
            reason: reason.into(),
        }
    }

    pub fn value(&self) -> Option<&T> {
        match self {
            Probed::Known { value } => Some(value),
            Probed::Unavailable { .. } => None,
        }
    }

    pub fn is_known(&self) -> bool {
        matches!(self, Probed::Known { .. })
    }

    /// Use `fallback` only when this value is unavailable.
    pub fn or_else(self, fallback: impl FnOnce() -> Probed<T>) -> Probed<T> {
        match self {
            Probed::Known { .. } => self,
            Probed::Unavailable { .. } => fallback(),
        }
    }
}

impl<T, E: std::fmt::Display> From<Result<T, E>> for Probed<T> {
    fn from(result: Result<T, E>) -> Self {
        match result {
            Ok(value) => Probed::known(value),
            Err(err) => Probed::unavailable(err.to_string()),
        }
    }
}

/// Static information about the running build, shown in Settings → About.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct AppInfo {
    pub name: String,
    pub version: String,
    /// `debug` or `release`.
    pub build_profile: String,
    /// Rust target OS, e.g. `windows`.
    pub target_os: String,
    /// Rust target architecture, e.g. `x86_64`.
    pub target_arch: String,
    /// Folder where log files are written, if it could be resolved.
    pub log_dir: Probed<String>,
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn known_serialises_with_status_tag() {
        let json = serde_json::to_value(Probed::known(16u32)).unwrap();
        assert_eq!(json, serde_json::json!({"status": "known", "value": 16}));
    }

    #[test]
    fn unavailable_serialises_with_reason() {
        let json = serde_json::to_value(Probed::<u32>::unavailable("WMI timed out")).unwrap();
        assert_eq!(
            json,
            serde_json::json!({"status": "unavailable", "reason": "WMI timed out"})
        );
    }

    #[test]
    fn round_trips() {
        let original = Probed::known("NVIDIA GeForce RTX 3060".to_string());
        let text = serde_json::to_string(&original).unwrap();
        assert_eq!(
            serde_json::from_str::<Probed<String>>(&text).unwrap(),
            original
        );
    }

    #[test]
    fn value_is_none_when_unavailable() {
        let probed = Probed::<u64>::unavailable("no permission");
        assert_eq!(probed.value(), None);
        assert!(!probed.is_known());
    }

    #[test]
    fn or_else_keeps_known_value() {
        let probed = Probed::known(8).or_else(|| Probed::known(4));
        assert_eq!(probed.value(), Some(&8));
    }

    #[test]
    fn or_else_uses_fallback_when_unavailable() {
        let probed = Probed::<u32>::unavailable("primary failed").or_else(|| Probed::known(4));
        assert_eq!(probed.value(), Some(&4));
    }

    #[test]
    fn app_info_uses_camel_case_for_the_frontend() {
        let info = AppInfo {
            name: "GameCheck".into(),
            version: "2.0.0".into(),
            build_profile: "release".into(),
            target_os: "windows".into(),
            target_arch: "x86_64".into(),
            log_dir: Probed::unavailable("no path"),
        };
        let json = serde_json::to_value(info).unwrap();
        assert_eq!(json["buildProfile"], "release");
        assert_eq!(json["targetArch"], "x86_64");
        assert_eq!(json["logDir"]["status"], "unavailable");
    }

    #[test]
    fn from_result_keeps_error_text() {
        let probed: Probed<u32> = Err::<u32, _>("access denied").into();
        assert_eq!(probed, Probed::unavailable("access denied"));
    }
}
