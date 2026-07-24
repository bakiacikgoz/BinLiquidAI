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

#[derive(Clone)]
struct BrowserSession {
    mode: BrowserMode,
    task_id: Option<String>,
    // Tauri/Wry does not expose a safe native history API for remote pages.
    // This records only addresses navigated through ImperaOS commands; it
    // never evaluates page script or trusts a remote page to report history.
    history: Vec<String>,
    history_index: usize,
}

#[derive(Default)]
pub struct BrowserSessionRegistry {
    sessions: Mutex<HashMap<String, BrowserSession>>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BrowserOpenRequest {
    pub mode: BrowserMode,
    pub url: String,
    pub task_id: Option<String>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BrowserNavigateRequest {
    pub label: String,
    pub url: String,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BrowserSessionRequest {
    pub label: String,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct BrowserHistoryState {
    pub can_back: bool,
    pub can_forward: bool,
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
    let host = parsed
        .host_str()
        .filter(|host| !host.is_empty())
        .map(|host| host.to_ascii_lowercase())
        .ok_or_else(|| "BROWSER_POLICY_DENIED: agent allowlist contains an invalid domain".to_owned())?;
    if host == "localhost" || host.parse::<std::net::IpAddr>().is_ok() {
        return Err("BROWSER_POLICY_DENIED: agent allowlist requires a DNS domain".into());
    }
    Ok(host)
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
    // Content and application-internal schemes are always denied. They are
    // not OS application launches, so an approval must never turn them into
    // an executable route.
    !matches!(
        url.scheme(),
        "http" | "https" | "file" | "javascript" | "data" | "tauri" | "asset"
    )
}

fn record_history_navigation(session: &mut BrowserSession, url: &str) {
    if session
        .history
        .get(session.history_index)
        .is_some_and(|current| current == url)
    {
        return;
    }
    if !session.history.is_empty() {
        session.history.truncate(session.history_index.saturating_add(1));
    }
    session.history.push(url.to_owned());
    session.history_index = session.history.len().saturating_sub(1);
}

fn history_target(session: &BrowserSession, direction: i8) -> Option<String> {
    let index = match direction {
        -1 => session.history_index.checked_sub(1)?,
        1 if session.history_index + 1 < session.history.len() => session.history_index + 1,
        _ => return None,
    };
    session.history.get(index).cloned()
}

fn move_history(session: &mut BrowserSession, direction: i8) -> Option<String> {
    let target = history_target(session, direction)?;
    session.history_index = match direction {
        -1 => session.history_index.checked_sub(1)?,
        1 => session.history_index + 1,
        _ => return None,
    };
    Some(target)
}

fn history_state(session: &BrowserSession) -> BrowserHistoryState {
    BrowserHistoryState {
        can_back: session.history_index > 0,
        can_forward: session.history_index + 1 < session.history.len(),
    }
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
    sessions: tauri::State<'_, BrowserSessionRegistry>,
    request: BrowserOpenRequest,
) -> Result<String, String> {
    let initial_url = Url::parse(&request.url).map_err(|_| "BROWSER_POLICY_DENIED: invalid URL")?;
    let session = BrowserSession {
        mode: request.mode.clone(),
        task_id: request.task_id.clone(),
        history: vec![initial_url.as_str().to_owned()],
        history_index: 0,
    };
    let label = open_browser_window(app, state.inner().clone(), request)?;
    sessions
        .sessions
        .lock()
        .map_err(|_| "BROWSER_POLICY_DENIED: browser session registry unavailable")?
        .insert(label.clone(), session);
    Ok(label)
}

#[tauri::command]
pub fn browser_navigate(
    app: AppHandle,
    state: tauri::State<'_, BrowserPolicyState>,
    sessions: tauri::State<'_, BrowserSessionRegistry>,
    request: BrowserNavigateRequest,
) -> Result<(), String> {
    let session = sessions
        .sessions
        .lock()
        .map_err(|_| "BROWSER_POLICY_DENIED: browser session registry unavailable")?
        .get(&request.label)
        .cloned()
        .ok_or_else(|| "BROWSER_POLICY_DENIED: unknown browser session")?;
    let url = Url::parse(&request.url).map_err(|_| "BROWSER_POLICY_DENIED: invalid URL")?;
    if !allowed(&state, &session.mode, session.task_id.as_deref(), &url) {
        return Err("BROWSER_POLICY_DENIED: URL is not allowed for this browser mode".into());
    }
    app.get_webview_window(&request.label)
        .ok_or_else(|| "BROWSER_POLICY_DENIED: browser session is no longer available")?
        .navigate(url.clone())
        .map_err(|_| "BROWSER_POLICY_DENIED: browser could not navigate".to_owned())?;
    let mut sessions = sessions
        .sessions
        .lock()
        .map_err(|_| "BROWSER_POLICY_DENIED: browser session registry unavailable")?;
    let session = sessions
        .get_mut(&request.label)
        .ok_or_else(|| "BROWSER_POLICY_DENIED: unknown browser session")?;
    record_history_navigation(session, url.as_str());
    Ok(())
}

fn browser_move_history(
    app: &AppHandle,
    policy: &BrowserPolicyState,
    sessions: &BrowserSessionRegistry,
    label: &str,
    direction: i8,
) -> Result<(), String> {
    let (mode, task_id, target) = {
        let sessions = sessions
            .sessions
            .lock()
            .map_err(|_| "BROWSER_POLICY_DENIED: browser session registry unavailable")?;
        let session = sessions
            .get(label)
            .ok_or_else(|| "BROWSER_POLICY_DENIED: unknown browser session")?;
        (
            session.mode.clone(),
            session.task_id.clone(),
            history_target(session, direction)
                .ok_or_else(|| "BROWSER_POLICY_DENIED: browser history is unavailable")?,
        )
    };
    let target_url = Url::parse(&target).map_err(|_| "BROWSER_POLICY_DENIED: invalid browser history URL")?;
    if !allowed(policy, &mode, task_id.as_deref(), &target_url) {
        return Err("BROWSER_POLICY_DENIED: browser history target is not allowed for this mode".into());
    }
    app.get_webview_window(label)
        .ok_or_else(|| "BROWSER_POLICY_DENIED: browser session is no longer available")?
        .navigate(target_url)
        .map_err(|_| "BROWSER_POLICY_DENIED: browser could not navigate history".to_owned())?;
    let mut sessions = sessions
        .sessions
        .lock()
        .map_err(|_| "BROWSER_POLICY_DENIED: browser session registry unavailable")?;
    let session = sessions
        .get_mut(label)
        .ok_or_else(|| "BROWSER_POLICY_DENIED: unknown browser session")?;
    let moved = move_history(session, direction);
    if moved.as_deref() != Some(target.as_str()) {
        return Err("BROWSER_POLICY_DENIED: browser history changed during navigation".into());
    }
    Ok(())
}

#[tauri::command]
pub fn browser_back(
    app: AppHandle,
    state: tauri::State<'_, BrowserPolicyState>,
    sessions: tauri::State<'_, BrowserSessionRegistry>,
    request: BrowserSessionRequest,
) -> Result<(), String> {
    browser_move_history(&app, state.inner(), sessions.inner(), &request.label, -1)
}

#[tauri::command]
pub fn browser_forward(
    app: AppHandle,
    state: tauri::State<'_, BrowserPolicyState>,
    sessions: tauri::State<'_, BrowserSessionRegistry>,
    request: BrowserSessionRequest,
) -> Result<(), String> {
    browser_move_history(&app, state.inner(), sessions.inner(), &request.label, 1)
}

#[tauri::command]
pub fn browser_history_state(
    sessions: tauri::State<'_, BrowserSessionRegistry>,
    request: BrowserSessionRequest,
) -> Result<BrowserHistoryState, String> {
    let sessions = sessions
        .sessions
        .lock()
        .map_err(|_| "BROWSER_POLICY_DENIED: browser session registry unavailable")?;
    let session = sessions
        .get(&request.label)
        .ok_or_else(|| "BROWSER_POLICY_DENIED: unknown browser session")?;
    Ok(history_state(session))
}

#[tauri::command]
pub fn browser_reload(
    app: AppHandle,
    sessions: tauri::State<'_, BrowserSessionRegistry>,
    request: BrowserSessionRequest,
) -> Result<(), String> {
    if !sessions
        .sessions
        .lock()
        .map_err(|_| "BROWSER_POLICY_DENIED: browser session registry unavailable")?
        .contains_key(&request.label)
    {
        return Err("BROWSER_POLICY_DENIED: unknown browser session".into());
    }
    app.get_webview_window(&request.label)
        .ok_or_else(|| "BROWSER_POLICY_DENIED: browser session is no longer available")?
        .reload()
        .map_err(|_| "BROWSER_POLICY_DENIED: browser could not reload".to_owned())
}

#[tauri::command]
pub fn browser_close(
    app: AppHandle,
    sessions: tauri::State<'_, BrowserSessionRegistry>,
    request: BrowserSessionRequest,
) -> Result<(), String> {
    let known = sessions
        .sessions
        .lock()
        .map_err(|_| "BROWSER_POLICY_DENIED: browser session registry unavailable")?
        .remove(&request.label)
        .is_some();
    if !known {
        return Err("BROWSER_POLICY_DENIED: unknown browser session".into());
    }
    if let Some(window) = app.get_webview_window(&request.label) {
        window
            .close()
            .map_err(|_| "BROWSER_POLICY_DENIED: browser could not close")?;
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{
        allowed, is_external_application_scheme, move_history, record_history_navigation,
        BrowserMode, BrowserPolicyState, BrowserSession,
    };
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
        assert!(state
            .set_agent_domains_from_governed_policy("task-1", ["localhost"])
            .is_err());
        assert!(state
            .set_agent_domains_from_governed_policy("task-1", ["127.0.0.1"])
            .is_err());
    }

    #[test]
    fn blocked_content_schemes_are_never_treated_as_external_applications() {
        for value in [
            "file:///tmp/secret",
            "javascript:alert(1)",
            "data:text/html,blocked",
            "tauri://localhost/",
            "asset://localhost/icon.svg",
        ] {
            assert!(
                !is_external_application_scheme(&url(value)),
                "{value} must stay blocked without an approval route"
            );
        }
        assert!(is_external_application_scheme(&url("mailto:operator@example.com")));
    }

    #[test]
    fn history_tracks_only_explicit_native_navigations() {
        let mut session = BrowserSession {
            mode: BrowserMode::User,
            task_id: None,
            history: Vec::new(),
            history_index: 0,
        };
        record_history_navigation(&mut session, "https://imperaos.dev/");
        record_history_navigation(&mut session, "https://imperaos.dev/docs");
        record_history_navigation(&mut session, "https://imperaos.dev/releases");

        assert_eq!(move_history(&mut session, -1), Some("https://imperaos.dev/docs".to_string()));
        assert_eq!(move_history(&mut session, -1), Some("https://imperaos.dev/".to_string()));
        assert_eq!(move_history(&mut session, -1), None);
        assert_eq!(move_history(&mut session, 1), Some("https://imperaos.dev/docs".to_string()));

        record_history_navigation(&mut session, "https://imperaos.dev/security");
        assert_eq!(move_history(&mut session, 1), None);
    }
}
