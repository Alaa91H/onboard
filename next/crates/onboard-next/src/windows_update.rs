//! Update discovery for signed, stable Windows releases.
//!
//! This module never downloads or launches an installer. It only reads the
//! latest public GitHub release in a background thread and returns a candidate
//! that the user can inspect. Applying an update is deliberately deferred until
//! the stable-release pipeline signs installers and verifies their checksums.

use serde::Deserialize;
use std::cmp::Ordering;
use std::sync::mpsc::{self, Receiver};
use std::thread;
use std::time::{Duration, SystemTime, UNIX_EPOCH};

const RELEASE_ENDPOINT: &str = "https://api.github.com/repos/Alaa91H/onboard/releases/latest";
const CHECK_INTERVAL: Duration = Duration::from_secs(24 * 60 * 60);

#[derive(Clone, Debug, Eq, PartialEq)]
pub struct UpdateOffer {
    pub version: String,
    pub release_url: String,
    pub installer_url: Option<String>,
    pub installer_sha256: Option<String>,
}

#[derive(Clone, Debug, Eq, PartialEq)]
pub enum UpdateStatus {
    Idle,
    Checking,
    UpToDate,
    Available(UpdateOffer),
    NoPublishedRelease,
    Unavailable(String),
}

pub struct UpdateCheck {
    receiver: Receiver<UpdateStatus>,
}

impl UpdateCheck {
    pub fn try_receive(&self) -> Option<UpdateStatus> {
        self.receiver.try_recv().ok()
    }
}

#[derive(Deserialize)]
struct GitHubRelease {
    tag_name: String,
    html_url: String,
    draft: bool,
    prerelease: bool,
    assets: Vec<GitHubAsset>,
}

#[derive(Deserialize)]
struct GitHubAsset {
    name: String,
    browser_download_url: String,
    digest: Option<String>,
}

pub fn should_check(last_checked_at: Option<u64>, now: SystemTime) -> bool {
    let Some(last_checked_at) = last_checked_at else {
        return true;
    };
    let now = unix_seconds(now);
    now.saturating_sub(last_checked_at) >= CHECK_INTERVAL.as_secs()
}

pub fn unix_seconds(time: SystemTime) -> u64 {
    time.duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}

pub fn start_background_check(current_version: String, architecture: &str) -> UpdateCheck {
    let (sender, receiver) = mpsc::channel();
    let architecture = architecture.to_owned();
    thread::spawn(move || {
        let status = check_latest_release(&current_version, &architecture);
        let _ = sender.send(status);
    });
    UpdateCheck { receiver }
}

fn check_latest_release(current_version: &str, architecture: &str) -> UpdateStatus {
    let response = match ureq::get(RELEASE_ENDPOINT)
        .set("Accept", "application/vnd.github+json")
        .set("User-Agent", "Onboard-Next-updater")
        .set("X-GitHub-Api-Version", "2026-03-10")
        .timeout(Duration::from_secs(10))
        .call()
    {
        Ok(response) => response,
        Err(ureq::Error::Status(404, _)) => return UpdateStatus::NoPublishedRelease,
        Err(error) => return UpdateStatus::Unavailable(format!("تعذر فحص التحديثات: {error}")),
    };
    let body = match response.into_string() {
        Ok(body) => body,
        Err(error) => return UpdateStatus::Unavailable(format!("تعذر قراءة الإصدار: {error}")),
    };
    let release: GitHubRelease = match serde_json::from_str(&body) {
        Ok(release) => release,
        Err(error) => {
            return UpdateStatus::Unavailable(format!("بيانات الإصدار غير صالحة: {error}"))
        }
    };
    if release.draft || release.prerelease {
        return UpdateStatus::NoPublishedRelease;
    }
    let version = release.tag_name.trim_start_matches('v').to_owned();
    if compare_versions(&version, current_version) != Ordering::Greater {
        return UpdateStatus::UpToDate;
    }
    let expected_name = format!("windows-{architecture}-setup.exe");
    let installer = release
        .assets
        .iter()
        .find(|asset| asset.name.ends_with(&expected_name));
    let installer_url = installer.map(|asset| asset.browser_download_url.clone());
    let installer_sha256 = installer.and_then(|asset| {
        asset
            .digest
            .as_deref()
            .and_then(|digest| digest.strip_prefix("sha256:"))
            .map(str::to_owned)
    });
    UpdateStatus::Available(UpdateOffer {
        version,
        release_url: release.html_url,
        installer_url,
        installer_sha256,
    })
}

fn compare_versions(left: &str, right: &str) -> Ordering {
    let parse = |value: &str| {
        let mut parts = value
            .split('.')
            .map(|part| part.parse::<u32>().unwrap_or(0));
        (
            parts.next().unwrap_or(0),
            parts.next().unwrap_or(0),
            parts.next().unwrap_or(0),
        )
    };
    parse(left).cmp(&parse(right))
}

#[cfg(test)]
mod tests {
    use super::{compare_versions, should_check, unix_seconds, CHECK_INTERVAL};
    use std::cmp::Ordering;
    use std::time::{Duration, SystemTime, UNIX_EPOCH};

    #[test]
    fn version_comparison_handles_semantic_version_order() {
        assert_eq!(compare_versions("1.5.0", "1.4.4"), Ordering::Greater);
        assert_eq!(compare_versions("1.4.4", "1.4.4"), Ordering::Equal);
        assert_eq!(compare_versions("1.4.3", "1.4.4"), Ordering::Less);
    }

    #[test]
    fn update_check_is_limited_to_once_per_day() {
        let now = UNIX_EPOCH + Duration::from_secs(2 * CHECK_INTERVAL.as_secs());
        let recent = unix_seconds(now) - CHECK_INTERVAL.as_secs() + 1;
        assert!(!should_check(Some(recent), now));
        assert!(should_check(Some(recent - 1), now));
        assert!(should_check(None, SystemTime::now()));
    }
}
