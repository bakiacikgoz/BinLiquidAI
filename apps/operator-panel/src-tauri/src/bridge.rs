use serde::{Deserialize, Serialize};
use serde_json::Value;
use std::collections::HashMap;
use std::fs::{self, File};
use std::io::{BufRead, BufReader, Read, Seek, SeekFrom};
use std::path::{Component, Path, PathBuf};
use std::process::Stdio;
use std::time::Duration;
use tokio::process::Command;

const CONTRACT_VERSION: &str = "1.0";
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
    artifact_name: String,
    payload: Value,
    truncated: bool,
    bytes_read: usize,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct TailEventsPayload {
    events: Vec<Value>,
    next_cursor: u64,
    reset: bool,
    truncated: bool,
    bad_line_count: u64,
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
pub async fn bridge_handshake(config: BridgeConfig) -> BridgeResult<HandshakePayload> {
    let profile = config.profile();
    let version = match run_cli_text(&config, vec!["--version".to_string()]).await {
        Ok(text) => text.lines().next().unwrap_or_default().trim().to_string(),
        Err(error) => return BridgeResult::err(error),
    };

    let capabilities = match run_cli_json(&config, vec!["operator", "capabilities", "--json"]).await
    {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };

    let doctor = match run_cli_json(&config, vec!["doctor", "--profile", profile.as_str()]).await {
        Ok(value) => value,
        Err(error) => return BridgeResult::err(error),
    };

    let resolved = match resolve_cli_command(&config) {
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

fn resolve_cli_command(config: &BridgeConfig) -> Result<ResolvedCli, BridgeError> {
    let mode = parse_core_mode(config.mode.as_deref());

    let cli_path = config
        .cli_path
        .as_deref()
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(str::to_string);

    let bundled_path = config
        .bundled_python_path
        .as_deref()
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
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
    let contents = current.parent()?.parent()?;
    let path = contents.join("Resources/binliquid-runtime/python/bin/python");
    if path.exists() {
        Some(path)
    } else {
        None
    }
}

fn configure_cli_env(command: &mut Command, config: &BridgeConfig, resolved: &ResolvedCli) {
    command.env_clear();

    match resolved.mode {
        CoreMode::Bundled => {
            let runtime_path = Path::new(&resolved.program)
                .parent()
                .map(|value| value.to_string_lossy().to_string())
                .unwrap_or_default();
            let system_path = "/usr/bin:/bin:/usr/sbin:/sbin";
            if runtime_path.is_empty() {
                command.env("PATH", system_path);
            } else {
                command.env("PATH", format!("{runtime_path}:{system_path}"));
            }
        }
        _ => {
            if let Ok(path) = std::env::var("PATH") {
                command.env("PATH", path);
            }
        }
    }

    for key in ["HOME", "USER", "TMPDIR", "TMP", "TEMP", "LANG", "LC_ALL"] {
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

async fn run_cli_text(config: &BridgeConfig, args: Vec<String>) -> Result<String, BridgeError> {
    let output = run_cli_raw(config, args).await?;
    Ok(output.stdout)
}

async fn run_cli_json(config: &BridgeConfig, args: Vec<&str>) -> Result<Value, BridgeError> {
    let owned = args
        .into_iter()
        .map(ToString::to_string)
        .collect::<Vec<_>>();
    run_cli_json_owned(config, owned).await
}

async fn run_cli_json_owned(
    config: &BridgeConfig,
    args: Vec<String>,
) -> Result<Value, BridgeError> {
    let output = run_cli_raw(config, args).await?;
    parse_json_output(&output)
}

async fn run_cli_raw(
    config: &BridgeConfig,
    args: Vec<String>,
) -> Result<RawCliOutput, BridgeError> {
    let config = config.clone();
    let resolved = resolve_cli_command(&config)?;
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
    use std::io::Write;

    #[test]
    fn normalize_actor_requires_expected_format() {
        assert!(normalize_actor("ops-1").is_ok());
        assert!(normalize_actor(" ").is_err());
        assert!(normalize_actor("a*").is_err());
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
}
