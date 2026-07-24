use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::path::PathBuf;
use std::sync::{Arc, Mutex};
use tauri::{
    webview::{DownloadEvent, NewWindowResponse},
    AppHandle, Emitter, Manager, Url, WebviewUrl, WebviewWindowBuilder,
};

#[derive(Clone, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub enum BrowserMode {
    User,
    Preview,
    Agent,
}

#[derive(Clone, Default)]
pub struct BrowserPolicyState {
    // Arcs are intentional: redirect handlers must observe runtime policy
    // changes instead of holding a stale policy snapshot.
    preview_origins: Arc<Mutex<HashSet<String>>>,
    agent_domains: Arc<Mutex<HashMap<String, HashSet<String>>>>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BrowserOpenRequest {
    pub mode: BrowserMode,
    pub url: String,
    pub task_id: Option<String>,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "snake_case")]
enum BrowserApprovalKind {
    NewWindow,
    Download,
    ExternalApplication,
}

#[derive(Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct BrowserApprovalRequest {
    kind: BrowserApprovalKind,
    url: String,
    mode: BrowserMode,
    task_id: Option<String>,
}

fn origin(url: &Url) -> String {
    format!(
        "{}://{}{}",
        url.scheme(),
        url.host_str().unwrap_or_default(),
        url.port().map(|p| format!(":{p}")).unwrap_or_default()
    )
}

fn normalize_agent_domain(value: &str) -> Result<String, String> {
    let candidate = value.trim().to_ascii_lowercase();
    if candidate.is_empty()
        || candidate.contains('/')
        || candidate.contains('@')
        || candidate.contains(':')
    {
        return Err("BROWSER_POLICY_DENIED: agent allowlist contains an invalid domain".into());
    }
    let parsed = Url::parse(&format!("https://{candidate}"))
        .map_err(|_| "BROWSER_POLICY_DENIED: agent allowlist contains an invalid domain")?;
    parsed
        .host_str()
        .filter(|host| !host.is_empty())
        .map(|host| host.to_ascii_lowercase())
        .ok_or_else(|| "BROWSER_POLICY_DENIED: agent allowlist contains an invalid domain".into())
}

impl BrowserPolicyState {
    pub fn with_runtime_preview_origins() -> Self {
        let state = Self::default();
        // The desktop dev runtime owns this port through tauri.conf.json; no
        // renderer input can extend the preview registry.
        if cfg!(debug_assertions) {
            let _ = state.register_preview_origin("http://localhost:5173");
        }
        state
    }

    /// Called only by trusted runtime/deployment-policy code. This deliberately
    /// has no Tauri command so renderer code cannot forge a preview origin.
    pub fn register_preview_origin(&self, origin_value: &str) -> Result<(), String> {
        let url = Url::parse(origin_value)
            .map_err(|_| "BROWSER_POLICY_DENIED: invalid preview origin")?;
        if !matches!(url.scheme(), "http" | "https")
            || !matches!(url.host_str(), Some("localhost") | Some("127.0.0.1"))
            || url.port().is_none()
            || url.path() != "/"
            || url.query().is_some()
            || url.fragment().is_some()
        {
            return Err(
                "BROWSER_POLICY_DENIED: preview origin must be registered localhost with port"
                    .into(),
            );
        }
        self.preview_origins
            .lock()
            .map_err(|_| "BROWSER_POLICY_DENIED: policy unavailable")?
            .insert(origin(&url));
        Ok(())
    }

    /// Replaces, rather than extends, a task's allowlist after the trusted
    /// task/deployment policy evaluator has validated it.
    pub fn set_agent_domains_from_governed_policy<I, S>(
        &self,
        task_id: &str,
        domains: I,
    ) -> Result<(), String>
    where
        I: IntoIterator<Item = S>,
        S: AsRef<str>,
    {
        if task_id.trim().is_empty() {
            return Err("BROWSER_POLICY_DENIED: agent policy requires a task".into());
        }
        let normalized = domains
            .into_iter()
            .map(|value| normalize_agent_domain(value.as_ref()))
            .collect::<Result<HashSet<_>, _>>()?;
        self.agent_domains
            .lock()
            .map_err(|_| "BROWSER_POLICY_DENIED: policy unavailable")?
            .insert(task_id.to_owned(), normalized);
        Ok(())
    }

    pub fn preview_origins(&self) -> Result<Vec<String>, String> {
        let mut origins = self
            .preview_origins
            .lock()
            .map_err(|_| "BROWSER_POLICY_DENIED: policy unavailable")?
            .iter()
            .cloned()
            .collect::<Vec<_>>();
        origins.sort();
        Ok(origins)
    }
}

fn allowed(
    state: &BrowserPolicyState,
    mode: &BrowserMode,
    task_id: Option<&str>,
    url: &Url,
) -> bool {
    match mode {
        BrowserMode::User => url.scheme() == "https",
        BrowserMode::Preview => {
            if !matches!(url.scheme(), "http" | "https")
                || !matches!(url.host_str(), Some("localhost") | Some("127.0.0.1"))
            {
                return false;
            }
            state
                .preview_origins
                .lock()
                .ok()
                .is_some_and(|origins| origins.contains(&origin(url)))
        }
        BrowserMode::Agent => task_id
            .and_then(|id| {
                state
                    .agent_domains
                    .lock()
                    .ok()
                    .and_then(|domains| domains.get(id).cloned())
            })
            .is_some_and(|domains| {
                url.scheme() == "https"
                    && url
                        .host_str()
                        .is_some_and(|host| domains.contains(&host.to_ascii_lowercase()))
            }),
    }
}

fn profile_directory(app: &AppHandle, mode: &BrowserMode) -> Result<PathBuf, String> {
    let profile = match mode {
        BrowserMode::User => "user".to_owned(),
        BrowserMode::Preview => "preview".to_owned(),
        // Every agent window receives a fresh profile, so it cannot use a
        // user's cookies or another agent's session.
        BrowserMode::Agent => format!("agent/{}", uuid::Uuid::new_v4()),
    };
    let directory = app
        .path()
        .app_data_dir()
        .map_err(|_| "BROWSER_POLICY_DENIED: browser profile location unavailable")?
        .join("browser-profiles")
        .join(profile);
    std::fs::create_dir_all(&directory)
        .map_err(|_| "BROWSER_POLICY_DENIED: browser profile location unavailable")?;
    Ok(directory)
}

fn emit_approval_required(
    app: &AppHandle,
    kind: BrowserApprovalKind,
    url: &Url,
    mode: &BrowserMode,
    task_id: Option<&str>,
) {
    let _ = app.emit(
        "browser://approval-required",
        BrowserApprovalRequest {
            kind,
            url: url.as_str().to_owned(),
            mode: mode.clone(),
            task_id: task_id.map(ToOwned::to_owned),
        },
    );
}

fn is_external_application_scheme(url: &Url) -> bool {
    !matches!(url.scheme(), "http" | "https")
}

fn open_browser_window(
    app: AppHandle,
    policy: BrowserPolicyState,
    request: BrowserOpenRequest,
) -> Result<String, String> {
    let url = Url::parse(&request.url).map_err(|_| "BROWSER_POLICY_DENIED: invalid URL")?;
    if !allowed(&policy, &request.mode, request.task_id.as_deref(), &url) {
        return Err("BROWSER_POLICY_DENIED: URL is not allowed for this browser mode".into());
    }
    let mode = request.mode;
    let task_id = request.task_id;
    let label = format!("imperaos-browser-{}", uuid::Uuid::new_v4());
    let navigation_policy = policy.clone();
    let navigation_mode = mode.clone();
    let navigation_task_id = task_id.clone();
    let navigation_app = app.clone();
    let popup_policy = policy.clone();
    let popup_mode = mode.clone();
    let popup_task_id = task_id.clone();
    let popup_app = app.clone();
    let download_policy = policy;
    let download_mode = mode.clone();
    let download_task_id = task_id.clone();
    let download_app = app.clone();
    WebviewWindowBuilder::new(&app, &label, WebviewUrl::External(url))
        .data_directory(profile_directory(&app, &mode)?)
        // Every redirect is checked against the live policy state.
        .on_navigation(move |target| {
            let permitted = allowed(
                &navigation_policy,
                &navigation_mode,
                navigation_task_id.as_deref(),
                target,
            );
            if !permitted && is_external_application_scheme(target) {
                emit_approval_required(
                    &navigation_app,
                    BrowserApprovalKind::ExternalApplication,
                    target,
                    &navigation_mode,
                    navigation_task_id.as_deref(),
                );
            }
            permitted
        })
        // Popups never inherit an ambient approval. They are denied until the
        // main product UI asks the user and opens a separately governed window.
        .on_new_window(move |target, _features| {
            if allowed(
                &popup_policy,
                &popup_mode,
                popup_task_id.as_deref(),
                &target,
            ) {
                emit_approval_required(
                    &popup_app,
                    BrowserApprovalKind::NewWindow,
                    &target,
                    &popup_mode,
                    popup_task_id.as_deref(),
                );
            } else if is_external_application_scheme(&target) {
                emit_approval_required(
                    &popup_app,
                    BrowserApprovalKind::ExternalApplication,
                    &target,
                    &popup_mode,
                    popup_task_id.as_deref(),
                );
            }
            NewWindowResponse::Deny
        })
        // A browser download is not an artifact export. It stays denied until
        // a future governed save/approval workflow is supplied by the host.
        .on_download(move |_webview, event| {
            if let DownloadEvent::Requested { url, .. } = event {
                if allowed(
                    &download_policy,
                    &download_mode,
                    download_task_id.as_deref(),
                    &url,
                ) {
                    emit_approval_required(
                        &download_app,
                        BrowserApprovalKind::Download,
                        &url,
                        &download_mode,
                        download_task_id.as_deref(),
                    );
                }
            }
            false
        })
        .build()
        .map_err(|_| "BROWSER_POLICY_DENIED: child webview could not open")?;
    Ok(label)
}

#[tauri::command]
pub fn browser_list_preview_origins(
    state: tauri::State<'_, BrowserPolicyState>,
) -> Result<Vec<String>, String> {
    state.preview_origins()
}

#[tauri::command]
pub fn browser_open(
    app: AppHandle,
    state: tauri::State<'_, BrowserPolicyState>,
    request: BrowserOpenRequest,
) -> Result<String, String> {
    open_browser_window(app, state.inner().clone(), request)
}

#[cfg(test)]
mod tests {
    use super::{allowed, BrowserMode, BrowserPolicyState};
    use tauri::Url;

    fn url(value: &str) -> Url {
        Url::parse(value).expect("valid test URL")
    }

    #[test]
    fn user_mode_allows_only_explicit_https_addresses() {
        let state = BrowserPolicyState::default();
        for value in [
            "https://imperaos.dev/",
            "https://localhost:4444/",
            "https://127.0.0.1:4444/",
        ] {
            assert!(allowed(&state, &BrowserMode::User, None, &url(value)));
        }
        for value in [
            "http://imperaos.dev/",
            "file:///tmp/secret",
            "javascript:alert(1)",
            "data:text/html,blocked",
            "tauri://localhost/",
            "asset://localhost/icon.svg",
        ] {
            assert!(!allowed(&state, &BrowserMode::User, None, &url(value)));
        }
    }

    #[test]
    fn preview_mode_requires_a_runtime_registered_exact_origin() {
        let state = BrowserPolicyState::default();
        assert!(state
            .register_preview_origin("http://localhost:4173")
            .is_ok());
        assert!(allowed(
            &state,
            &BrowserMode::Preview,
            None,
            &url("http://localhost:4173/path")
        ));
        assert!(!allowed(
            &state,
            &BrowserMode::Preview,
            None,
            &url("http://localhost:4174/path")
        ));
        assert!(!allowed(
            &state,
            &BrowserMode::Preview,
            None,
            &url("https://localhost:4173/path")
        ));
        assert!(!allowed(
            &state,
            &BrowserMode::Preview,
            None,
            &url("http://127.0.0.1:4173/path")
        ));
        assert!(state.register_preview_origin("http://localhost").is_err());
        assert_eq!(state.preview_origins().unwrap(), ["http://localhost:4173"]);
    }

    #[test]
    fn agent_mode_is_scoped_to_a_governed_task_allowlist() {
        let state = BrowserPolicyState::default();
        state
            .set_agent_domains_from_governed_policy("task-1", ["api.example.com"])
            .expect("trusted policy registration");
        assert!(allowed(
            &state,
            &BrowserMode::Agent,
            Some("task-1"),
            &url("https://api.example.com/v1")
        ));
        assert!(!allowed(
            &state,
            &BrowserMode::Agent,
            Some("task-2"),
            &url("https://api.example.com/v1")
        ));
        assert!(!allowed(
            &state,
            &BrowserMode::Agent,
            Some("task-1"),
            &url("http://api.example.com/v1")
        ));
        assert!(!allowed(
            &state,
            &BrowserMode::Agent,
            Some("task-1"),
            &url("https://www.example.com/v1")
        ));
    }
}
