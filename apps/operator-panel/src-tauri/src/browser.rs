use serde::{Deserialize, Serialize};
use std::collections::{HashMap, HashSet};
use std::sync::{Arc, Mutex};
use tauri::{AppHandle, Url, WebviewUrl, WebviewWindowBuilder};

#[derive(Clone, Deserialize, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub enum BrowserMode {
    User,
    Preview,
    Agent,
}

#[derive(Default)]
pub struct BrowserPolicyState {
    preview_origins: Mutex<HashSet<String>>,
    agent_domains: Mutex<HashMap<String, HashSet<String>>>,
}

impl Clone for BrowserPolicyState {
    fn clone(&self) -> Self {
        Self {
            preview_origins: Mutex::new(
                self.preview_origins
                    .lock()
                    .map(|items| items.clone())
                    .unwrap_or_default(),
            ),
            agent_domains: Mutex::new(
                self.agent_domains
                    .lock()
                    .map(|items| items.clone())
                    .unwrap_or_default(),
            ),
        }
    }
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BrowserOpenRequest {
    pub mode: BrowserMode,
    pub url: String,
    pub task_id: Option<String>,
}

fn origin(url: &Url) -> String {
    format!(
        "{}://{}{}",
        url.scheme(),
        url.host_str().unwrap_or_default(),
        url.port().map(|p| format!(":{p}")).unwrap_or_default()
    )
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
                url.scheme() == "https" && url.host_str().is_some_and(|host| domains.contains(host))
            }),
    }
}

#[tauri::command]
pub fn browser_register_preview_origin(
    state: tauri::State<'_, BrowserPolicyState>,
    origin_value: String,
) -> Result<(), String> {
    let url =
        Url::parse(&origin_value).map_err(|_| "BROWSER_POLICY_DENIED: invalid preview origin")?;
    if !matches!(url.scheme(), "http" | "https")
        || !matches!(url.host_str(), Some("localhost") | Some("127.0.0.1"))
        || url.port().is_none()
    {
        return Err(
            "BROWSER_POLICY_DENIED: preview origin must be registered localhost with port".into(),
        );
    }
    state
        .preview_origins
        .lock()
        .map_err(|_| "BROWSER_POLICY_DENIED: policy unavailable")?
        .insert(origin(&url));
    Ok(())
}

#[tauri::command]
pub fn browser_open(
    app: AppHandle,
    state: tauri::State<'_, BrowserPolicyState>,
    request: BrowserOpenRequest,
) -> Result<String, String> {
    let url = Url::parse(&request.url).map_err(|_| "BROWSER_POLICY_DENIED: invalid URL")?;
    if !allowed(&state, &request.mode, request.task_id.as_deref(), &url) {
        return Err("BROWSER_POLICY_DENIED: URL is not allowed for this browser mode".into());
    }
    let policy = Arc::new(state.inner().clone());
    let mode = request.mode.clone();
    let task_id = request.task_id.clone();
    let label = format!("imperaos-browser-{}", uuid::Uuid::new_v4());
    WebviewWindowBuilder::new(&app, &label, WebviewUrl::External(url))
        .on_navigation(move |target| allowed(&policy, &mode, task_id.as_deref(), target))
        .build()
        .map_err(|_| "BROWSER_POLICY_DENIED: child webview could not open")?;
    Ok(label)
}
