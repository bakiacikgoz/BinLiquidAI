use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use std::fs::{self, File};
use std::io::{BufRead, BufReader, Read, Seek, SeekFrom};
use std::path::{Component, Path, PathBuf};
use std::process::Stdio;
use std::time::{Duration, SystemTime, UNIX_EPOCH};
use tauri::Manager;
use tokio::process::Command;

const CONTRACT_VERSION: &str = "2.0";
const DEFAULT_TIMEOUT_MS: u64 = 15_000;
const DEFAULT_MAX_BYTES: usize = 256 * 1024;
const DEFAULT_MAX_LINES: usize = 500;

const ARTIFACT_ALLOWLIST: &[&str] = &[
    "status.json",
    "tasks.json",
    "handoffs.json",
    "audit_envelope.json",
    "events.jsonl",
];

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct BridgeError {
    code: String,
    message: String,
    stderr_preview: String,
    command: String,
    retryable: bool,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct BridgeResult<T: Serialize> {
    ok: bool,
    data: Option<T>,
    error: Option<BridgeError>,
}

impl<T: Serialize> BridgeResult<T> {
    fn ok(data: T) -> Self {
        Self {
            ok: true,
            data: Some(data),
            error: None,
        }
    }

    fn err(error: BridgeError) -> Self {
        Self {
            ok: false,
            data: None,
            error: Some(error),
        }
    }
}

impl BridgeError {
    fn new(
        code: &str,
        message: impl Into<String>,
        stderr_preview: impl Into<String>,
        command: impl Into<String>,
        retryable: bool,
    ) -> Self {
        Self {
            code: code.to_string(),
            message: message.into(),
            stderr_preview: stderr_preview.into(),
            command: command.into(),
            retryable,
        }
    }
}

#[derive(Debug, Deserialize, Clone)]
#[serde(rename_all = "camelCase")]
pub struct BridgeConfig {
    pub mode: Option<String>,
    pub cli_path: Option<String>,
    pub bundled_python_path: Option<String>,
    pub profile: Option<String>,
    pub root_dir: Option<String>,
    #[serde(default)]
    pub env: HashMap<String, String>,
    pub timeout_ms: Option<u64>,
}

impl BridgeConfig {
    fn profile(&self) -> String {
        self.profile
            .as_deref()
            .map(str::trim)
            .filter(|value| !value.is_empty())
            .unwrap_or("balanced")
            .to_string()
    }

    fn root_dir(&self) -> String {
        self.root_dir
            .as_deref()
            .map(str::trim)
            .filter(|value| !value.is_empty())
            .unwrap_or(".binliquid/team/jobs")
            .to_string()
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum CoreMode {
    Auto,
    External,
    Bundled,
}

#[derive(Debug)]
struct ResolvedCli {
    mode: CoreMode,
    program: String,
    prefix_args: Vec<String>,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct HandshakePayload {
    ui_version: String,
    core_version: String,
    profile: String,
    contract_version: String,
    capabilities: Value,
    doctor: Value,
    root_dir: String,
    mode: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ReadArtifactPayload {
    contract_version: String,
    artifact_name: String,
    payload: Value,
    truncated: bool,
    bytes_read: usize,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct TailEventsPayload {
    contract_version: String,
    events: Vec<Value>,
    next_cursor: u64,
    reset: bool,
    truncated: bool,
    bad_line_count: u64,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct SpawnedRunPayload {
    contract_version: String,
    job_id: String,
    profile: String,
    root_dir: String,
    process_id: Option<u32>,
}

#[derive(Debug)]
struct RawCliOutput {
    stdout: String,
    stderr: String,
    command: String,
}

#[derive(Debug)]
struct TailOutcome {
    events: Vec<Value>,
    next_cursor: u64,
    reset: bool,
    truncated: bool,
    bad_line_count: u64,
}

#[tauri::command]
pub async fn bridge_handshake(
    app: tauri::AppHandle,
    config: BridgeConfig,
) -> BridgeResult<HandshakePayload> {
    let profile = config.profile();
    let resource_dir = app_resource_dir(&app);
    let version = match run_cli_text_with_resource_dir(
        &config,
        vec!["--version".to_string()],
        resource_dir.as_deref(),
    )
    .await
    {
        Ok(text) => text.lines().next().unwrap_or_default().trim().to_string(),
        Err(error) => return BridgeResult::err(error),
    };

    let capabilities = match run_cli_json_with_resource_dir(
        &config,
        vec!["operator", "capabilities", "--json"],
        resource_dir.as_deref(),
    )
    .await
    {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };

    let doctor = match run_cli_json_with_resource_dir(
        &config,
        vec!["doctor", "--profile", profile.as_str()],
        resource_dir.as_deref(),
    )
    .await
    {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };

    let resolved = match resolve_cli_command(&config, resource_dir.as_deref()) {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };

    BridgeResult::ok(HandshakePayload {
        ui_version: env!("CARGO_PKG_VERSION").to_string(),
        core_version: version,
        profile,
        contract_version: CONTRACT_VERSION.to_string(),
        capabilities,
        doctor,
        root_dir: config.root_dir(),
        mode: core_mode_name(resolved.mode).to_string(),
    })
}

#[tauri::command]
pub async fn bridge_approval_pending(config: BridgeConfig) -> BridgeResult<Value> {
    match run_cli_json_owned(
        &config,
        vec![
            "approval".to_string(),
            "pending".to_string(),
            "--profile".to_string(),
            config.profile(),
            "--json".to_string(),
        ],
    )
    .await
    {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_approval_show(
    config: BridgeConfig,
    approval_id: String,
) -> BridgeResult<Value> {
    if approval_id.trim().is_empty() {
        return BridgeResult::err(BridgeError::new(
            "INVALID_INPUT",
            "approval_id is required",
            "",
            "approval show",
            false,
        ));
    }
    match run_cli_json_owned(
        &config,
        vec![
            "approval".to_string(),
            "show".to_string(),
            "--id".to_string(),
            approval_id.trim().to_string(),
            "--profile".to_string(),
            config.profile(),
            "--json".to_string(),
        ],
    )
    .await
    {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_approval_decide(
    config: BridgeConfig,
    approval_id: String,
    approve: bool,
    reason: Option<String>,
    operator_id: String,
) -> BridgeResult<Value> {
    let actor = match normalize_actor(&operator_id) {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };

    let mut args = vec![
        "approval".to_string(),
        "decide".to_string(),
        "--id".to_string(),
        approval_id.trim().to_string(),
        if approve {
            "--approve".to_string()
        } else {
            "--reject".to_string()
        },
        "--actor".to_string(),
        actor,
        "--profile".to_string(),
        config.profile(),
    ];
    if let Some(value) = reason {
        let normalized = value.trim();
        if !normalized.is_empty() {
            args.push("--reason".to_string());
            args.push(normalized.to_string());
        }
    }

    match run_cli_json_owned(&config, args).await {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_approval_execute(
    config: BridgeConfig,
    approval_id: String,
    operator_id: String,
) -> BridgeResult<Value> {
    let actor = match normalize_actor(&operator_id) {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };

    match run_cli_json_owned(
        &config,
        vec![
            "approval".to_string(),
            "execute".to_string(),
            "--id".to_string(),
            approval_id.trim().to_string(),
            "--actor".to_string(),
            actor,
            "--profile".to_string(),
            config.profile(),
        ],
    )
    .await
    {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_team_list(config: BridgeConfig, since: Option<String>) -> BridgeResult<Value> {
    let mut args = vec![
        "team".to_string(),
        "list".to_string(),
        "--root-dir".to_string(),
        config.root_dir(),
        "--json".to_string(),
    ];
    if let Some(value) = since {
        let normalized = value.trim();
        if !normalized.is_empty() {
            args.push("--since".to_string());
            args.push(normalized.to_string());
        }
    }

    match run_cli_json_owned(&config, args).await {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_team_submit(
    config: BridgeConfig,
    spec_path: String,
    request: String,
    case_id: Option<String>,
    job_id: Option<String>,
    provider: Option<String>,
    fallback_provider: Option<String>,
    model: Option<String>,
    hf_model_id: Option<String>,
) -> BridgeResult<SpawnedRunPayload> {
    let spec = match normalize_required_path(&spec_path, "spec_path", "team run") {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };
    let request = match normalize_required_text(&request, "request", "team run") {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };
    let run_job_id = match job_id.as_deref().map(normalize_job_id).transpose() {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };

    let generated_job_id = run_job_id.unwrap_or_else(generate_job_id);
    let mut args = vec![
        "team".to_string(),
        "run".to_string(),
        "--spec".to_string(),
        spec,
        "--once".to_string(),
        request,
        "--job-id".to_string(),
        generated_job_id.clone(),
        "--profile".to_string(),
        config.profile(),
        "--json".to_string(),
    ];
    push_optional_arg(&mut args, "--case-id", case_id.as_deref());
    push_optional_arg(&mut args, "--provider", provider.as_deref());
    push_optional_arg(
        &mut args,
        "--fallback-provider",
        fallback_provider.as_deref(),
    );
    push_optional_arg(&mut args, "--model", model.as_deref());
    push_optional_arg(&mut args, "--hf-model-id", hf_model_id.as_deref());

    match spawn_cli_background(&config, args).await {
        Ok(process_id) => BridgeResult::ok(SpawnedRunPayload {
            contract_version: CONTRACT_VERSION.to_string(),
            job_id: generated_job_id,
            profile: config.profile(),
            root_dir: config.root_dir(),
            process_id,
        }),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_team_resume_submit(
    config: BridgeConfig,
    spec_path: String,
    source_job_id: String,
    resume_job_id: Option<String>,
    provider: Option<String>,
    fallback_provider: Option<String>,
    model: Option<String>,
    hf_model_id: Option<String>,
) -> BridgeResult<SpawnedRunPayload> {
    let spec = match normalize_required_path(&spec_path, "spec_path", "team resume") {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };
    let source_job_id = match normalize_job_id(&source_job_id) {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };
    let resume_job_id = match resume_job_id.as_deref().map(normalize_job_id).transpose() {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };
    let generated_job_id = resume_job_id.unwrap_or_else(|| format!("{source_job_id}-resume-ui"));
    let mut args = vec![
        "team".to_string(),
        "resume".to_string(),
        "--spec".to_string(),
        spec,
        "--job-id".to_string(),
        source_job_id,
        "--resume-job-id".to_string(),
        generated_job_id.clone(),
        "--root-dir".to_string(),
        config.root_dir(),
        "--profile".to_string(),
        config.profile(),
        "--json".to_string(),
    ];
    push_optional_arg(&mut args, "--provider", provider.as_deref());
    push_optional_arg(
        &mut args,
        "--fallback-provider",
        fallback_provider.as_deref(),
    );
    push_optional_arg(&mut args, "--model", model.as_deref());
    push_optional_arg(&mut args, "--hf-model-id", hf_model_id.as_deref());

    match spawn_cli_background(&config, args).await {
        Ok(process_id) => BridgeResult::ok(SpawnedRunPayload {
            contract_version: CONTRACT_VERSION.to_string(),
            job_id: generated_job_id,
            profile: config.profile(),
            root_dir: config.root_dir(),
            process_id,
        }),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_computer_use_submit(
    config: BridgeConfig,
    request: String,
    case_id: Option<String>,
    job_id: Option<String>,
    mode: Option<String>,
    runtime: Option<String>,
    provider: Option<String>,
    fallback_provider: Option<String>,
    model: Option<String>,
    hf_model_id: Option<String>,
) -> BridgeResult<SpawnedRunPayload> {
    let request = match normalize_required_text(&request, "request", "computer-use run") {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };
    let run_job_id = match job_id.as_deref().map(normalize_job_id).transpose() {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };
    let generated_job_id = run_job_id.unwrap_or_else(generate_job_id);
    let mut args = vec![
        "computer-use".to_string(),
        "run".to_string(),
        "--once".to_string(),
        request,
        "--job-id".to_string(),
        generated_job_id.clone(),
        "--root-dir".to_string(),
        config.root_dir(),
        "--profile".to_string(),
        config.profile(),
        "--json".to_string(),
    ];
    push_optional_arg(&mut args, "--case-id", case_id.as_deref());
    push_optional_arg(&mut args, "--mode", mode.as_deref());
    let runtime = match normalize_computer_use_runtime(runtime.as_deref()) {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };
    push_optional_arg(&mut args, "--runtime", runtime.as_deref());
    push_optional_arg(&mut args, "--provider", provider.as_deref());
    push_optional_arg(
        &mut args,
        "--fallback-provider",
        fallback_provider.as_deref(),
    );
    push_optional_arg(&mut args, "--model", model.as_deref());
    push_optional_arg(&mut args, "--hf-model-id", hf_model_id.as_deref());

    match spawn_cli_background(&config, args).await {
        Ok(process_id) => BridgeResult::ok(SpawnedRunPayload {
            contract_version: CONTRACT_VERSION.to_string(),
            job_id: generated_job_id,
            profile: config.profile(),
            root_dir: config.root_dir(),
            process_id,
        }),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_computer_use_summary(
    config: BridgeConfig,
    limit: Option<u32>,
) -> BridgeResult<Value> {
    let mut args = vec![
        "computer-use".to_string(),
        "summary".to_string(),
        "--root-dir".to_string(),
        config.root_dir(),
        "--profile".to_string(),
        config.profile(),
        "--json".to_string(),
    ];
    if let Some(value) = limit {
        args.push("--limit".to_string());
        args.push(value.clamp(1, 200).to_string());
    }

    match run_cli_json_owned(&config, args).await {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_computer_use_pause(
    config: BridgeConfig,
    job_id: String,
) -> BridgeResult<Value> {
    let normalized = match normalize_job_id(&job_id) {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };
    match run_cli_json_owned(
        &config,
        vec![
            "computer-use".to_string(),
            "pause".to_string(),
            "--job-id".to_string(),
            normalized,
            "--root-dir".to_string(),
            config.root_dir(),
            "--profile".to_string(),
            config.profile(),
            "--json".to_string(),
        ],
    )
    .await
    {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_computer_use_resume(
    config: BridgeConfig,
    job_id: String,
) -> BridgeResult<Value> {
    let normalized = match normalize_job_id(&job_id) {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };
    match run_cli_json_owned(
        &config,
        vec![
            "computer-use".to_string(),
            "resume".to_string(),
            "--job-id".to_string(),
            normalized,
            "--root-dir".to_string(),
            config.root_dir(),
            "--profile".to_string(),
            config.profile(),
            "--json".to_string(),
        ],
    )
    .await
    {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_computer_use_stop(config: BridgeConfig, job_id: String) -> BridgeResult<Value> {
    let normalized = match normalize_job_id(&job_id) {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };
    match run_cli_json_owned(
        &config,
        vec![
            "computer-use".to_string(),
            "stop".to_string(),
            "--job-id".to_string(),
            normalized,
            "--root-dir".to_string(),
            config.root_dir(),
            "--profile".to_string(),
            config.profile(),
            "--json".to_string(),
        ],
    )
    .await
    {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_computer_use_state(
    config: BridgeConfig,
    job_id: String,
) -> BridgeResult<Value> {
    let normalized = match normalize_job_id(&job_id) {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };
    match run_cli_json_owned(
        &config,
        vec![
            "computer-use".to_string(),
            "state".to_string(),
            "--job-id".to_string(),
            normalized,
            "--root-dir".to_string(),
            config.root_dir(),
            "--profile".to_string(),
            config.profile(),
            "--json".to_string(),
        ],
    )
    .await
    {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_team_replay(config: BridgeConfig, job_id: String) -> BridgeResult<Value> {
    let normalized = match normalize_job_id(&job_id) {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };

    match run_cli_json_owned(
        &config,
        vec![
            "team".to_string(),
            "replay".to_string(),
            "--job-id".to_string(),
            normalized,
            "--root-dir".to_string(),
            config.root_dir(),
            "--json".to_string(),
        ],
    )
    .await
    {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_team_status(config: BridgeConfig, job_id: String) -> BridgeResult<Value> {
    let normalized = match normalize_job_id(&job_id) {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };

    match run_cli_json_owned(
        &config,
        vec![
            "team".to_string(),
            "status".to_string(),
            "--job-id".to_string(),
            normalized,
            "--root-dir".to_string(),
            config.root_dir(),
            "--json".to_string(),
        ],
    )
    .await
    {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_team_export(
    config: BridgeConfig,
    job_id: String,
    export_dir: String,
) -> BridgeResult<Value> {
    let normalized = match normalize_job_id(&job_id) {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };
    let export_path = export_dir.trim();
    if export_path.is_empty() {
        return BridgeResult::err(BridgeError::new(
            "INVALID_INPUT",
            "export_dir is required",
            "",
            "team artifacts",
            false,
        ));
    }

    match run_cli_json_owned(
        &config,
        vec![
            "team".to_string(),
            "artifacts".to_string(),
            "--job-id".to_string(),
            normalized,
            "--root-dir".to_string(),
            config.root_dir(),
            "--export".to_string(),
            export_path.to_string(),
        ],
    )
    .await
    {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_config_resolve(
    config: BridgeConfig,
    provider: Option<String>,
    fallback_provider: Option<String>,
    model: Option<String>,
    hf_model_id: Option<String>,
) -> BridgeResult<Value> {
    let mut args = vec![
        "config".to_string(),
        "resolve".to_string(),
        "--profile".to_string(),
        config.profile(),
        "--json".to_string(),
    ];
    push_optional_arg(&mut args, "--provider", provider.as_deref());
    push_optional_arg(
        &mut args,
        "--fallback-provider",
        fallback_provider.as_deref(),
    );
    push_optional_arg(&mut args, "--model", model.as_deref());
    push_optional_arg(&mut args, "--hf-model-id", hf_model_id.as_deref());

    match run_cli_json_owned(&config, args).await {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_auth_whoami(config: BridgeConfig) -> BridgeResult<Value> {
    match run_cli_json_owned(
        &config,
        vec![
            "auth".to_string(),
            "whoami".to_string(),
            "--profile".to_string(),
            config.profile(),
            "--json".to_string(),
        ],
    )
    .await
    {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_auth_check(config: BridgeConfig, permission: String) -> BridgeResult<Value> {
    let permission = match normalize_required_text(&permission, "permission", "auth check") {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };
    match run_cli_json_owned(
        &config,
        vec![
            "auth".to_string(),
            "check".to_string(),
            "--profile".to_string(),
            config.profile(),
            "--permission".to_string(),
            permission,
            "--json".to_string(),
        ],
    )
    .await
    {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_security_baseline(config: BridgeConfig) -> BridgeResult<Value> {
    match run_cli_json_owned(
        &config,
        vec![
            "security".to_string(),
            "baseline".to_string(),
            "--profile".to_string(),
            config.profile(),
            "--json".to_string(),
        ],
    )
    .await
    {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_keys_status(config: BridgeConfig) -> BridgeResult<Value> {
    match run_cli_json_owned(
        &config,
        vec![
            "keys".to_string(),
            "status".to_string(),
            "--profile".to_string(),
            config.profile(),
            "--json".to_string(),
        ],
    )
    .await
    {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_keys_verify(config: BridgeConfig, path: String) -> BridgeResult<Value> {
    let path = match normalize_required_text(&path, "path", "keys verify") {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };
    match run_cli_json_owned(
        &config,
        vec![
            "keys".to_string(),
            "verify".to_string(),
            "--profile".to_string(),
            config.profile(),
            "--path".to_string(),
            path,
            "--json".to_string(),
        ],
    )
    .await
    {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_keys_rotate_plan(
    config: BridgeConfig,
    next_key_id: Option<String>,
    activate_at: Option<String>,
    retire_after: Option<String>,
) -> BridgeResult<Value> {
    let mut args = vec![
        "keys".to_string(),
        "rotate-plan".to_string(),
        "--profile".to_string(),
        config.profile(),
        "--json".to_string(),
    ];
    push_optional_arg(&mut args, "--next-key-id", next_key_id.as_deref());
    push_optional_arg(&mut args, "--activate-at", activate_at.as_deref());
    push_optional_arg(&mut args, "--retire-after", retire_after.as_deref());

    match run_cli_json_owned(&config, args).await {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_support_bundle_export(
    config: BridgeConfig,
    output: Option<String>,
) -> BridgeResult<Value> {
    let mut args = vec![
        "support".to_string(),
        "bundle".to_string(),
        "export".to_string(),
        "--profile".to_string(),
        config.profile(),
        "--json".to_string(),
    ];
    push_optional_arg(&mut args, "--output", output.as_deref());
    match run_cli_json_owned(&config, args).await {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_backup_create(
    config: BridgeConfig,
    output_dir: Option<String>,
) -> BridgeResult<Value> {
    let mut args = vec![
        "backup".to_string(),
        "create".to_string(),
        "--profile".to_string(),
        config.profile(),
        "--json".to_string(),
    ];
    push_optional_arg(&mut args, "--output-dir", output_dir.as_deref());
    match run_cli_json_owned(&config, args).await {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_backup_verify(config: BridgeConfig, backup_dir: String) -> BridgeResult<Value> {
    let backup_dir = match normalize_required_text(&backup_dir, "backup_dir", "backup verify") {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };
    match run_cli_json_owned(
        &config,
        vec![
            "backup".to_string(),
            "verify".to_string(),
            "--profile".to_string(),
            config.profile(),
            "--backup-dir".to_string(),
            backup_dir,
            "--json".to_string(),
        ],
    )
    .await
    {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_restore_verify(
    config: BridgeConfig,
    backup_dir: String,
) -> BridgeResult<Value> {
    let backup_dir = match normalize_required_text(&backup_dir, "backup_dir", "restore verify") {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };
    match run_cli_json_owned(
        &config,
        vec![
            "restore".to_string(),
            "verify".to_string(),
            "--profile".to_string(),
            config.profile(),
            "--backup-dir".to_string(),
            backup_dir,
            "--json".to_string(),
        ],
    )
    .await
    {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_migrate_plan(config: BridgeConfig) -> BridgeResult<Value> {
    match run_cli_json_owned(
        &config,
        vec![
            "migrate".to_string(),
            "plan".to_string(),
            "--profile".to_string(),
            config.profile(),
            "--json".to_string(),
        ],
    )
    .await
    {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_migrate_apply_dry_run(config: BridgeConfig) -> BridgeResult<Value> {
    match run_cli_json_owned(
        &config,
        vec![
            "migrate".to_string(),
            "apply".to_string(),
            "--profile".to_string(),
            config.profile(),
            "--dry-run".to_string(),
            "--json".to_string(),
        ],
    )
    .await
    {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_metrics_snapshot(config: BridgeConfig) -> BridgeResult<Value> {
    match run_cli_json_owned(
        &config,
        vec![
            "metrics".to_string(),
            "snapshot".to_string(),
            "--profile".to_string(),
            config.profile(),
            "--json".to_string(),
        ],
    )
    .await
    {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_ga_readiness(
    config: BridgeConfig,
    report: Option<String>,
    qualification_report: Option<String>,
) -> BridgeResult<Value> {
    let mut args = vec![
        "ga".to_string(),
        "readiness".to_string(),
        "--profile".to_string(),
        config.profile(),
        "--json".to_string(),
    ];
    push_optional_arg(&mut args, "--report", report.as_deref());
    push_optional_arg(
        &mut args,
        "--qualification-report",
        qualification_report.as_deref(),
    );
    match run_cli_json_owned(&config, args).await {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_qualification_run(
    config: BridgeConfig,
    mode: Option<String>,
    soak_hours: Option<f64>,
    output_root: Option<String>,
    workloads: Option<String>,
    merge_from_report: Option<String>,
    provider: Option<String>,
    fallback_provider: Option<String>,
    model: Option<String>,
    hf_model_id: Option<String>,
) -> BridgeResult<Value> {
    let mut args = vec![
        "qualification".to_string(),
        "run".to_string(),
        "--profile".to_string(),
        config.profile(),
        "--json".to_string(),
    ];
    push_optional_arg(&mut args, "--mode", mode.as_deref());
    if let Some(hours) = soak_hours {
        args.push("--soak-hours".to_string());
        args.push(hours.to_string());
    }
    push_optional_arg(&mut args, "--output-root", output_root.as_deref());
    push_optional_arg(&mut args, "--workloads", workloads.as_deref());
    push_optional_arg(
        &mut args,
        "--merge-from-report",
        merge_from_report.as_deref(),
    );
    push_optional_arg(&mut args, "--provider", provider.as_deref());
    push_optional_arg(
        &mut args,
        "--fallback-provider",
        fallback_provider.as_deref(),
    );
    push_optional_arg(&mut args, "--model", model.as_deref());
    push_optional_arg(&mut args, "--hf-model-id", hf_model_id.as_deref());

    match run_cli_json_owned(&config, args).await {
        Ok(value) => BridgeResult::ok(value),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_read_artifact(
    root_dir: String,
    job_id: String,
    artifact_name: String,
    max_bytes: Option<usize>,
) -> BridgeResult<ReadArtifactPayload> {
    match read_artifact_impl(&root_dir, &job_id, &artifact_name, max_bytes) {
        Ok(payload) => BridgeResult::ok(payload),
        Err(error) => BridgeResult::err(error),
    }
}

#[tauri::command]
pub async fn bridge_tail_events(
    root_dir: String,
    job_id: String,
    cursor: Option<u64>,
    max_bytes: Option<usize>,
    max_lines: Option<usize>,
) -> BridgeResult<TailEventsPayload> {
    match tail_events_impl(
        &root_dir,
        &job_id,
        cursor.unwrap_or(0),
        max_bytes.unwrap_or(DEFAULT_MAX_BYTES),
        max_lines.unwrap_or(DEFAULT_MAX_LINES),
    ) {
        Ok(result) => BridgeResult::ok(TailEventsPayload {
            contract_version: CONTRACT_VERSION.to_string(),
            events: result.events,
            next_cursor: result.next_cursor,
            reset: result.reset,
            truncated: result.truncated,
            bad_line_count: result.bad_line_count,
        }),
        Err(error) => BridgeResult::err(error),
    }
}

fn parse_core_mode(value: Option<&str>) -> CoreMode {
    match value.map(|item| item.trim().to_lowercase()) {
        Some(mode) if mode == "external" => CoreMode::External,
        Some(mode) if mode == "bundled" => CoreMode::Bundled,
        _ => CoreMode::Auto,
    }
}

fn core_mode_name(mode: CoreMode) -> &'static str {
    match mode {
        CoreMode::Auto => "auto",
        CoreMode::External => "external",
        CoreMode::Bundled => "bundled",
    }
}

fn app_resource_dir(app: &tauri::AppHandle) -> Option<PathBuf> {
    app.path().resource_dir().ok()
}

fn resolve_cli_command(
    config: &BridgeConfig,
    resource_dir: Option<&Path>,
) -> Result<ResolvedCli, BridgeError> {
    let mode = parse_core_mode(config.mode.as_deref());

    let cli_path = config
        .cli_path
        .as_deref()
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(str::to_string);

    let configured_bundled_path = config
        .bundled_python_path
        .as_deref()
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(PathBuf::from);

    let bundled_path = configured_bundled_path
        .or_else(|| resource_dir.and_then(resolve_bundled_python_from_resource_dir))
        .or_else(default_bundled_python_path);

    if mode == CoreMode::External {
        return Ok(ResolvedCli {
            mode,
            program: cli_path.unwrap_or_else(|| "binliquid".to_string()),
            prefix_args: vec![],
        });
    }

    if mode == CoreMode::Bundled {
        let python = bundled_path.ok_or_else(|| {
            BridgeError::new(
                "CLI_NOT_FOUND",
                "Bundled python runtime was not found.",
                "",
                "resolve bundled runtime",
                false,
            )
        })?;

        return Ok(ResolvedCli {
            mode,
            program: python.to_string_lossy().to_string(),
            prefix_args: vec!["-m".to_string(), "binliquid".to_string()],
        });
    }

    if let Some(path) = cli_path {
        return Ok(ResolvedCli {
            mode: CoreMode::External,
            program: path,
            prefix_args: vec![],
        });
    }

    if let Some(path) = bundled_path {
        return Ok(ResolvedCli {
            mode: CoreMode::Bundled,
            program: path.to_string_lossy().to_string(),
            prefix_args: vec!["-m".to_string(), "binliquid".to_string()],
        });
    }

    Ok(ResolvedCli {
        mode: CoreMode::External,
        program: "binliquid".to_string(),
        prefix_args: vec![],
    })
}

fn default_bundled_python_path() -> Option<PathBuf> {
    let current = std::env::current_exe().ok()?;
    let exe_dir = current.parent()?;
    let mut resource_dirs = vec![exe_dir.join("resources"), exe_dir.to_path_buf()];

    if let Some(contents) = exe_dir.parent() {
        resource_dirs.push(contents.join("Resources"));
    }

    for resource_dir in resource_dirs {
        if let Some(path) = resolve_bundled_python_from_resource_dir(&resource_dir) {
            return Some(path);
        }
    }

    None
}

fn bundled_python_relative_path() -> &'static str {
    if cfg!(windows) {
        "binliquid-runtime/python/Scripts/python.exe"
    } else {
        "binliquid-runtime/python/bin/python"
    }
}

fn resolve_bundled_python_from_resource_dir(resource_dir: &Path) -> Option<PathBuf> {
    let path = resource_dir.join(bundled_python_relative_path());
    if path.exists() {
        Some(path)
    } else {
        None
    }
}

fn path_separator() -> &'static str {
    if cfg!(windows) {
        ";"
    } else {
        ":"
    }
}

fn fallback_system_path() -> &'static str {
    if cfg!(windows) {
        r"C:\Windows\System32;C:\Windows;C:\Windows\System32\Wbem"
    } else {
        "/usr/bin:/bin:/usr/sbin:/sbin"
    }
}

fn push_optional_arg(args: &mut Vec<String>, flag: &str, value: Option<&str>) {
    if let Some(raw) = value {
        let normalized = raw.trim();
        if !normalized.is_empty() {
            args.push(flag.to_string());
            args.push(normalized.to_string());
        }
    }
}

fn normalize_required_text(value: &str, field: &str, command: &str) -> Result<String, BridgeError> {
    let normalized = value.trim();
    if normalized.is_empty() {
        return Err(BridgeError::new(
            "INVALID_INPUT",
            format!("{field} is required"),
            "",
            command,
            false,
        ));
    }
    Ok(normalized.to_string())
}

fn normalize_required_path(value: &str, field: &str, command: &str) -> Result<String, BridgeError> {
    let normalized = normalize_required_text(value, field, command)?;
    let path = PathBuf::from(&normalized);
    if !path.exists() {
        return Err(BridgeError::new(
            "INVALID_INPUT",
            format!("{field} does not exist"),
            "",
            command,
            false,
        ));
    }
    Ok(normalized)
}

fn generate_job_id() -> String {
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap_or_default()
        .as_millis();
    format!("job-ui-{now}")
}

fn configure_cli_env(command: &mut Command, config: &BridgeConfig, resolved: &ResolvedCli) {
    command.env_clear();
    let base_path = std::env::var("PATH").unwrap_or_else(|_| fallback_system_path().to_string());

    match resolved.mode {
        CoreMode::Bundled => {
            let runtime_path = Path::new(&resolved.program)
                .parent()
                .map(|value| value.to_string_lossy().to_string())
                .unwrap_or_default();
            if runtime_path.is_empty() {
                command.env("PATH", base_path);
            } else {
                command.env(
                    "PATH",
                    format!("{runtime_path}{}{base_path}", path_separator()),
                );
            }
        }
        _ => {
            command.env("PATH", base_path);
        }
    }

    let env_keys: &[&str] = if cfg!(windows) {
        &[
            "SystemRoot",
            "WINDIR",
            "USERPROFILE",
            "APPDATA",
            "LOCALAPPDATA",
            "PROGRAMDATA",
            "TEMP",
            "TMP",
            "ComSpec",
            "PATHEXT",
            "PROCESSOR_ARCHITECTURE",
            "NUMBER_OF_PROCESSORS",
        ]
    } else {
        &["HOME", "USER", "TMPDIR", "TMP", "TEMP", "LANG", "LC_ALL"]
    };

    for key in env_keys {
        if let Ok(value) = std::env::var(key) {
            command.env(key, value);
        }
    }

    command.env("PYTHONNOUSERSITE", "1");
    command.env("PYTHONDONTWRITEBYTECODE", "1");

    for (key, value) in &config.env {
        if key.starts_with("BINLIQUID_") {
            command.env(key, value);
        }
    }
}

async fn run_cli_text_with_resource_dir(
    config: &BridgeConfig,
    args: Vec<String>,
    resource_dir: Option<&Path>,
) -> Result<String, BridgeError> {
    let output = run_cli_raw_with_resource_dir(config, args, resource_dir).await?;
    Ok(output.stdout)
}

async fn run_cli_json_with_resource_dir(
    config: &BridgeConfig,
    args: Vec<&str>,
    resource_dir: Option<&Path>,
) -> Result<Value, BridgeError> {
    let owned = args
        .into_iter()
        .map(ToString::to_string)
        .collect::<Vec<_>>();
    run_cli_json_owned_with_resource_dir(config, owned, resource_dir).await
}

async fn run_cli_json_owned(
    config: &BridgeConfig,
    args: Vec<String>,
) -> Result<Value, BridgeError> {
    run_cli_json_owned_with_resource_dir(config, args, None).await
}

async fn run_cli_json_owned_with_resource_dir(
    config: &BridgeConfig,
    args: Vec<String>,
    resource_dir: Option<&Path>,
) -> Result<Value, BridgeError> {
    let output = run_cli_raw_with_resource_dir(config, args, resource_dir).await?;
    parse_json_output(&output)
}

async fn run_cli_raw_with_resource_dir(
    config: &BridgeConfig,
    args: Vec<String>,
    resource_dir: Option<&Path>,
) -> Result<RawCliOutput, BridgeError> {
    let config = config.clone();
    let resolved = resolve_cli_command(&config, resource_dir)?;
    let mut command = Command::new(&resolved.program);
    command.args(&resolved.prefix_args);
    command.args(&args);
    command.stdout(Stdio::piped());
    command.stderr(Stdio::piped());
    configure_cli_env(&mut command, &config, &resolved);

    let cmdline = format_command(&resolved.program, &resolved.prefix_args, &args);
    let timeout_ms = config.timeout_ms.unwrap_or(DEFAULT_TIMEOUT_MS);
    let output = tokio::time::timeout(Duration::from_millis(timeout_ms), command.output())
        .await
        .map_err(|_| {
            BridgeError::new(
                "TIMEOUT",
                format!("Command timed out after {timeout_ms}ms."),
                "",
                cmdline.clone(),
                true,
            )
        })?
        .map_err(|error| {
            let code = if error.kind() == std::io::ErrorKind::NotFound {
                "CLI_NOT_FOUND"
            } else {
                "CLI_FAILED"
            };
            BridgeError::new(
                code,
                error.to_string(),
                "",
                cmdline.clone(),
                code != "CLI_NOT_FOUND",
            )
        })?;

    let stdout = String::from_utf8_lossy(&output.stdout).to_string();
    let stderr = String::from_utf8_lossy(&output.stderr).to_string();

    if !output.status.success() {
        return Err(BridgeError::new(
            "CLI_FAILED",
            format!("Command exited with status {}", output.status),
            sanitize_preview(&stderr),
            cmdline,
            false,
        ));
    }

    Ok(RawCliOutput {
        stdout,
        stderr,
        command: cmdline,
    })
}

async fn spawn_cli_background(
    config: &BridgeConfig,
    args: Vec<String>,
) -> Result<Option<u32>, BridgeError> {
    let config = config.clone();
    let resolved = resolve_cli_command(&config, None)?;
    let mut command = Command::new(&resolved.program);
    command.args(&resolved.prefix_args);
    command.args(&args);
    command.stdout(Stdio::null());
    command.stderr(Stdio::null());
    configure_cli_env(&mut command, &config, &resolved);

    let child = command.spawn().map_err(|error| {
        let code = if error.kind() == std::io::ErrorKind::NotFound {
            "CLI_NOT_FOUND"
        } else {
            "CLI_FAILED"
        };
        BridgeError::new(
            code,
            error.to_string(),
            "",
            format_command(&resolved.program, &resolved.prefix_args, &args),
            code != "CLI_NOT_FOUND",
        )
    })?;
    Ok(child.id())
}

fn parse_json_output(output: &RawCliOutput) -> Result<Value, BridgeError> {
    let body = output.stdout.trim();
    serde_json::from_str(body).map_err(|error| {
        let stdout_preview = sanitize_preview(body);
        let stderr_preview = if output.stderr.trim().is_empty() {
            stdout_preview
        } else {
            sanitize_preview(&output.stderr)
        };
        BridgeError::new(
            "PARSE_FAILED",
            format!("Failed to parse CLI JSON output: {error}"),
            stderr_preview,
            output.command.clone(),
            false,
        )
    })
}

fn format_command(program: &str, prefix: &[String], args: &[String]) -> String {
    let mut parts = vec![program.to_string()];
    parts.extend(prefix.iter().cloned());
    parts.extend(args.iter().cloned());
    parts.join(" ")
}

fn sanitize_preview(text: &str) -> String {
    text.lines()
        .take(8)
        .map(str::trim)
        .filter(|line| !line.is_empty())
        .collect::<Vec<_>>()
        .join("\n")
}

fn normalize_actor(operator_id: &str) -> Result<String, BridgeError> {
    let normalized = operator_id.trim();
    let valid = normalized.len() >= 3
        && normalized.len() <= 64
        && normalized
            .chars()
            .all(|ch| ch.is_ascii_alphanumeric() || matches!(ch, '-' | '_' | '.'));
    if !valid {
        return Err(BridgeError::new(
            "INVALID_INPUT",
            "operator_id must be 3-64 chars using [a-zA-Z0-9._-]",
            "",
            "normalize actor",
            false,
        ));
    }
    Ok(format!("ui:{normalized}"))
}

fn normalize_job_id(job_id: &str) -> Result<String, BridgeError> {
    let normalized = job_id.trim();
    let valid = !normalized.is_empty()
        && normalized.len() <= 128
        && normalized
            .chars()
            .all(|ch| ch.is_ascii_alphanumeric() || matches!(ch, '-' | '_'));
    if !valid {
        return Err(BridgeError::new(
            "INVALID_INPUT",
            "Invalid job_id format.",
            "",
            "job_id validation",
            false,
        ));
    }
    Ok(normalized.to_string())
}

fn normalize_computer_use_runtime(value: Option<&str>) -> Result<Option<String>, BridgeError> {
    let Some(raw) = value else {
        return Ok(None);
    };
    let normalized = raw.trim().to_ascii_lowercase().replace('_', "-");
    if normalized.is_empty() {
        return Ok(None);
    }
    if matches!(
        normalized.as_str(),
        "legacy-pilot" | "vision-first" | "auto"
    ) {
        return Ok(Some(normalized));
    }
    Err(BridgeError::new(
        "INVALID_INPUT",
        "runtime must be legacy-pilot, vision-first, or auto",
        "",
        "computer-use run",
        false,
    ))
}

fn resolve_root_dir(root_dir: &str) -> Result<PathBuf, BridgeError> {
    let normalized = root_dir.trim();
    if normalized.is_empty() {
        return Err(BridgeError::new(
            "INVALID_INPUT",
            "root_dir is required",
            "",
            "root_dir",
            false,
        ));
    }

    let root = fs::canonicalize(normalized).map_err(|error| {
        BridgeError::new(
            "INVALID_INPUT",
            format!("Unable to resolve root_dir: {error}"),
            "",
            "root_dir",
            false,
        )
    })?;
    reject_symlink_segments(&root)?;
    Ok(root)
}

fn reject_symlink_segments(path: &Path) -> Result<(), BridgeError> {
    let mut current = PathBuf::new();
    for component in path.components() {
        match component {
            Component::Prefix(prefix) => current.push(prefix.as_os_str()),
            Component::RootDir => current.push(Path::new("/")),
            Component::CurDir => continue,
            Component::ParentDir => {
                return Err(BridgeError::new(
                    "PATH_VIOLATION",
                    "Parent directory segments are not allowed.",
                    "",
                    path.display().to_string(),
                    false,
                ));
            }
            Component::Normal(value) => current.push(value),
        }

        if let Ok(meta) = fs::symlink_metadata(&current) {
            if meta.file_type().is_symlink() {
                return Err(BridgeError::new(
                    "PATH_VIOLATION",
                    format!("Symlink segment is not allowed: {}", current.display()),
                    "",
                    current.display().to_string(),
                    false,
                ));
            }
        }
    }
    Ok(())
}

fn safe_artifact_path(
    root_dir: &str,
    job_id: &str,
    artifact_name: &str,
) -> Result<PathBuf, BridgeError> {
    let root = resolve_root_dir(root_dir)?;
    let normalized_job_id = normalize_job_id(job_id)?;

    if !ARTIFACT_ALLOWLIST.contains(&artifact_name) {
        return Err(BridgeError::new(
            "INVALID_INPUT",
            "Artifact is not allowlisted.",
            "",
            artifact_name,
            false,
        ));
    }

    let job_dir = root.join(normalized_job_id);
    reject_symlink_segments(&job_dir)?;

    let logical_path = job_dir.join(artifact_name);
    reject_symlink_segments(&logical_path)?;

    let canonical_before = fs::canonicalize(&logical_path).map_err(|error| {
        BridgeError::new(
            "INVALID_INPUT",
            format!("Artifact not found: {error}"),
            "",
            logical_path.display().to_string(),
            false,
        )
    })?;

    if !canonical_before.starts_with(&root) {
        return Err(BridgeError::new(
            "PATH_VIOLATION",
            "Artifact path escapes root_dir.",
            "",
            canonical_before.display().to_string(),
            false,
        ));
    }

    reject_symlink_segments(&canonical_before)?;

    let canonical_after = fs::canonicalize(&logical_path).map_err(|error| {
        BridgeError::new(
            "PATH_VIOLATION",
            format!("Artifact changed during validation: {error}"),
            "",
            logical_path.display().to_string(),
            false,
        )
    })?;

    if canonical_before != canonical_after {
        return Err(BridgeError::new(
            "PATH_VIOLATION",
            "Artifact changed during open (TOCTOU guard).",
            "",
            logical_path.display().to_string(),
            false,
        ));
    }

    Ok(canonical_before)
}

fn read_artifact_impl(
    root_dir: &str,
    job_id: &str,
    artifact_name: &str,
    max_bytes: Option<usize>,
) -> Result<ReadArtifactPayload, BridgeError> {
    let path = safe_artifact_path(root_dir, job_id, artifact_name)?;
    let max = max_bytes.unwrap_or(DEFAULT_MAX_BYTES);
    let (bytes, truncated) = read_file_bounded(&path, max)?;
    let parsed = serde_json::from_slice::<Value>(&bytes).map_err(|error| {
        BridgeError::new(
            "PARSE_FAILED",
            format!("Failed to parse artifact JSON: {error}"),
            sanitize_preview(&String::from_utf8_lossy(&bytes)),
            path.display().to_string(),
            false,
        )
    })?;

    Ok(ReadArtifactPayload {
        contract_version: CONTRACT_VERSION.to_string(),
        artifact_name: artifact_name.to_string(),
        payload: parsed,
        truncated,
        bytes_read: bytes.len(),
    })
}

fn read_file_bounded(path: &Path, max_bytes: usize) -> Result<(Vec<u8>, bool), BridgeError> {
    let mut file = File::open(path).map_err(|error| {
        BridgeError::new(
            "INVALID_INPUT",
            format!("Failed to open file: {error}"),
            "",
            path.display().to_string(),
            false,
        )
    })?;

    let mut take = file.by_ref().take((max_bytes as u64) + 1);
    let mut buffer = Vec::new();
    take.read_to_end(&mut buffer).map_err(|error| {
        BridgeError::new(
            "CLI_FAILED",
            format!("Failed to read file: {error}"),
            "",
            path.display().to_string(),
            true,
        )
    })?;

    let truncated = buffer.len() > max_bytes;
    if truncated {
        buffer.truncate(max_bytes);
    }

    Ok((buffer, truncated))
}

fn tail_events_impl(
    root_dir: &str,
    job_id: &str,
    cursor: u64,
    max_bytes: usize,
    max_lines: usize,
) -> Result<TailOutcome, BridgeError> {
    let path = safe_artifact_path(root_dir, job_id, "events.jsonl")?;
    let mut file = File::open(&path).map_err(|error| {
        BridgeError::new(
            "INVALID_INPUT",
            format!("Failed to open events file: {error}"),
            "",
            path.display().to_string(),
            false,
        )
    })?;

    let metadata_len = file
        .metadata()
        .map_err(|error| {
            BridgeError::new(
                "CLI_FAILED",
                format!("Failed to inspect events file: {error}"),
                "",
                path.display().to_string(),
                true,
            )
        })?
        .len();

    let mut effective_cursor = cursor;
    let mut reset = false;
    if cursor > metadata_len {
        effective_cursor = 0;
        reset = true;
    }

    file.seek(SeekFrom::Start(effective_cursor))
        .map_err(|error| {
            BridgeError::new(
                "CLI_FAILED",
                format!("Failed to seek events file: {error}"),
                "",
                path.display().to_string(),
                true,
            )
        })?;

    let mut reader = BufReader::new(file);
    let mut events = Vec::new();
    let mut bytes_used = 0usize;
    let mut lines_used = 0usize;
    let mut next_cursor = effective_cursor;
    let mut truncated = false;
    let mut bad_line_count = 0u64;

    loop {
        let line_start = reader.stream_position().map_err(|error| {
            BridgeError::new(
                "CLI_FAILED",
                format!("Failed to read stream position: {error}"),
                "",
                path.display().to_string(),
                true,
            )
        })?;

        let mut buffer = Vec::new();
        let bytes = reader.read_until(b'\n', &mut buffer).map_err(|error| {
            BridgeError::new(
                "CLI_FAILED",
                format!("Failed to read events file: {error}"),
                "",
                path.display().to_string(),
                true,
            )
        })?;

        if bytes == 0 {
            break;
        }

        if !buffer.ends_with(b"\n") {
            reader.seek(SeekFrom::Start(line_start)).map_err(|error| {
                BridgeError::new(
                    "CLI_FAILED",
                    format!("Failed to rewind partial line: {error}"),
                    "",
                    path.display().to_string(),
                    true,
                )
            })?;
            break;
        }

        if lines_used >= max_lines || (bytes_used + bytes) > max_bytes {
            truncated = true;
            reader.seek(SeekFrom::Start(line_start)).map_err(|error| {
                BridgeError::new(
                    "CLI_FAILED",
                    format!("Failed to rewind bounded read: {error}"),
                    "",
                    path.display().to_string(),
                    true,
                )
            })?;
            break;
        }

        lines_used += 1;
        bytes_used += bytes;
        next_cursor = line_start + (bytes as u64);

        match serde_json::from_slice::<Value>(&buffer) {
            Ok(value) => events.push(value),
            Err(_) => {
                bad_line_count += 1;
                truncated = true;
            }
        }
    }

    Ok(TailOutcome {
        events,
        next_cursor,
        reset,
        truncated,
        bad_line_count,
    })
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;
    use std::io::Write;
    #[cfg(unix)]
    use std::os::unix::fs::PermissionsExt;

    #[test]
    fn normalize_actor_requires_expected_format() {
        assert!(normalize_actor("ops-1").is_ok());
        assert!(normalize_actor(" ").is_err());
        assert!(normalize_actor("a*").is_err());
    }

    #[test]
    fn normalize_computer_use_runtime_allows_only_supported_values() {
        assert_eq!(
            normalize_computer_use_runtime(Some("vision_first")).expect("runtime"),
            Some("vision-first".to_string())
        );
        assert_eq!(
            normalize_computer_use_runtime(Some("legacy-pilot")).expect("runtime"),
            Some("legacy-pilot".to_string())
        );
        assert_eq!(
            normalize_computer_use_runtime(Some("auto")).expect("runtime"),
            Some("auto".to_string())
        );
        assert_eq!(
            normalize_computer_use_runtime(Some(" ")).expect("empty"),
            None
        );
        assert!(normalize_computer_use_runtime(Some("unsafe-live")).is_err());
    }

    #[test]
    fn tail_events_buffers_partial_line() {
        let dir = tempfile::tempdir().expect("tempdir");
        let root = dir.path().join("jobs");
        let job = root.join("job-1");
        fs::create_dir_all(&job).expect("mkdir");

        let mut file = File::create(job.join("events.jsonl")).expect("events");
        file.write_all(b"{\"event\":\"ok\"}\n{\"event\":\"partial\"")
            .expect("write");

        let result =
            tail_events_impl(root.to_string_lossy().as_ref(), "job-1", 0, 4096, 50).expect("tail");

        assert_eq!(result.events.len(), 1);
        assert_eq!(result.bad_line_count, 0);
        assert!(!result.truncated);
    }

    #[test]
    fn tail_events_resets_cursor_when_file_shrinks() {
        let dir = tempfile::tempdir().expect("tempdir");
        let root = dir.path().join("jobs");
        let job = root.join("job-2");
        fs::create_dir_all(&job).expect("mkdir");

        let mut file = File::create(job.join("events.jsonl")).expect("events");
        file.write_all(b"{\"event\":\"one\"}\n").expect("write");

        let result = tail_events_impl(root.to_string_lossy().as_ref(), "job-2", 999, 4096, 50)
            .expect("tail");

        assert!(result.reset);
        assert_eq!(result.events.len(), 1);
    }

    #[test]
    fn safe_artifact_path_rejects_traversal_job_id() {
        let dir = tempfile::tempdir().expect("tempdir");
        let root = dir.path().join("jobs");
        fs::create_dir_all(&root).expect("mkdir");

        let result = safe_artifact_path(root.to_string_lossy().as_ref(), "../evil", "status.json");
        assert!(result.is_err());
    }

    #[test]
    fn read_artifact_payload_serializes_contract_version() {
        let dir = tempfile::tempdir().expect("tempdir");
        let root = dir.path().join("jobs");
        let job = root.join("job-3");
        fs::create_dir_all(&job).expect("mkdir");
        fs::write(job.join("status.json"), "{\"job\":{\"job_id\":\"job-3\"}}").expect("write");

        let payload = read_artifact_impl(
            root.to_string_lossy().as_ref(),
            "job-3",
            "status.json",
            None,
        )
        .expect("artifact");
        let json = serde_json::to_value(payload).expect("serialize");

        assert_eq!(json["contractVersion"], CONTRACT_VERSION);
        assert_eq!(json["artifactName"], "status.json");
    }

    #[test]
    fn spawned_run_payload_serializes_contract_version() {
        let payload = SpawnedRunPayload {
            contract_version: CONTRACT_VERSION.to_string(),
            job_id: "job-4".to_string(),
            profile: "balanced".to_string(),
            root_dir: ".binliquid/team/jobs".to_string(),
            process_id: Some(4242),
        };
        let json = serde_json::to_value(payload).expect("serialize");

        assert_eq!(json["contractVersion"], CONTRACT_VERSION);
        assert_eq!(json["jobId"], "job-4");
    }

    #[test]
    fn bundled_python_relative_path_matches_platform() {
        let path = bundled_python_relative_path();
        if cfg!(windows) {
            assert_eq!(path, "binliquid-runtime/python/Scripts/python.exe");
        } else {
            assert_eq!(path, "binliquid-runtime/python/bin/python");
        }
    }

    #[test]
    fn resolve_bundled_python_from_resource_dir_detects_runtime() {
        let dir = tempfile::tempdir().expect("tempdir");
        let resource_dir = dir.path();
        let python = resource_dir.join(bundled_python_relative_path());
        fs::create_dir_all(python.parent().expect("parent")).expect("mkdir");
        fs::write(&python, "placeholder").expect("python");

        let resolved = resolve_bundled_python_from_resource_dir(resource_dir).expect("runtime");

        assert_eq!(resolved, python);
    }

    #[test]
    fn resolve_cli_command_auto_prefers_cli_path_then_bundled() {
        let dir = tempfile::tempdir().expect("tempdir");
        let bundled = dir.path().join("python");
        fs::write(&bundled, "placeholder").expect("python");
        let config = BridgeConfig {
            mode: Some("auto".to_string()),
            cli_path: Some("binliquid-custom".to_string()),
            bundled_python_path: Some(bundled.to_string_lossy().to_string()),
            profile: Some("balanced".to_string()),
            root_dir: None,
            env: HashMap::new(),
            timeout_ms: None,
        };

        let external = resolve_cli_command(&config, None).expect("external");
        assert_eq!(external.mode, CoreMode::External);
        assert_eq!(external.program, "binliquid-custom");

        let bundled_config = BridgeConfig {
            cli_path: None,
            ..config
        };
        let bundled = resolve_cli_command(&bundled_config, None).expect("bundled");
        assert_eq!(bundled.mode, CoreMode::Bundled);
        assert_eq!(bundled.prefix_args, vec!["-m", "binliquid"]);
    }

    #[test]
    fn resolve_cli_command_auto_prefers_cli_path_over_resource_runtime() {
        let dir = tempfile::tempdir().expect("tempdir");
        let resource_dir = dir.path().join("resources");
        let python = resource_dir.join(bundled_python_relative_path());
        fs::create_dir_all(python.parent().expect("parent")).expect("mkdir");
        fs::write(&python, "placeholder").expect("python");
        let config = BridgeConfig {
            mode: Some("auto".to_string()),
            cli_path: Some("binliquid-custom".to_string()),
            bundled_python_path: None,
            profile: Some("balanced".to_string()),
            root_dir: None,
            env: HashMap::new(),
            timeout_ms: None,
        };

        let resolved = resolve_cli_command(&config, Some(&resource_dir)).expect("external");

        assert_eq!(resolved.mode, CoreMode::External);
        assert_eq!(resolved.program, "binliquid-custom");
    }

    #[test]
    fn resolve_cli_command_auto_uses_resource_runtime_when_cli_absent() {
        let dir = tempfile::tempdir().expect("tempdir");
        let resource_dir = dir.path().join("resources");
        let python = resource_dir.join(bundled_python_relative_path());
        fs::create_dir_all(python.parent().expect("parent")).expect("mkdir");
        fs::write(&python, "placeholder").expect("python");
        let config = BridgeConfig {
            mode: Some("auto".to_string()),
            cli_path: None,
            bundled_python_path: None,
            profile: Some("balanced".to_string()),
            root_dir: None,
            env: HashMap::new(),
            timeout_ms: None,
        };

        let resolved = resolve_cli_command(&config, Some(&resource_dir)).expect("bundled");

        assert_eq!(resolved.mode, CoreMode::Bundled);
        assert_eq!(resolved.program, python.to_string_lossy());
        assert_eq!(resolved.prefix_args, vec!["-m", "binliquid"]);
    }

    #[test]
    fn path_separator_matches_platform() {
        if cfg!(windows) {
            assert_eq!(path_separator(), ";");
        } else {
            assert_eq!(path_separator(), ":");
        }
    }

    #[test]
    fn spawn_cli_background_returns_pid_for_external_script() {
        let dir = tempfile::tempdir().expect("tempdir");
        let root = dir.path().join("jobs");
        fs::create_dir_all(&root).expect("mkdir");
        let script = if cfg!(windows) {
            let path = dir.path().join("fake-binliquid.cmd");
            fs::write(&path, "@echo off\r\nping -n 2 127.0.0.1 >nul\r\n").expect("script");
            path
        } else {
            let path = dir.path().join("fake-binliquid.sh");
            fs::write(&path, "#!/bin/sh\nsleep 1\n").expect("script");
            path
        };
        #[cfg(unix)]
        fs::set_permissions(&script, fs::Permissions::from_mode(0o755)).expect("chmod");

        let config = BridgeConfig {
            mode: Some("external".to_string()),
            cli_path: Some(script.to_string_lossy().to_string()),
            bundled_python_path: None,
            profile: Some("balanced".to_string()),
            root_dir: Some(root.to_string_lossy().to_string()),
            env: HashMap::new(),
            timeout_ms: Some(1_000),
        };

        let runtime = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .expect("runtime");
        let pid = runtime
            .block_on(spawn_cli_background(&config, vec!["noop".to_string()]))
            .expect("spawn");

        assert!(pid.is_some());
    }
}
