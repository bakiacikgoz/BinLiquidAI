use serde::Serialize;
use sha2::{Digest, Sha256};
use std::collections::HashMap;
#[cfg(not(windows))]
use std::fs::File;
use std::fs::{self, OpenOptions};
use std::io::Write;
use std::path::{Path, PathBuf};
use std::time::{Duration, Instant};
use tokio::sync::Mutex;
use uuid::Uuid;

pub const DEFAULT_MAX_EXPORT_BYTES: usize = 100 * 1024 * 1024;
pub const DEFAULT_TICKET_TTL: Duration = Duration::from_secs(5 * 60);
const MAX_TICKET_TTL: Duration = Duration::from_secs(15 * 60);

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ExportBinding {
    workspace_id: String,
    principal_id: String,
    principal_type: String,
    export_id: String,
    artifact_id: String,
    revision_id: String,
    format: String,
}

impl ExportBinding {
    pub fn new(
        workspace_id: impl Into<String>,
        principal_id: impl Into<String>,
    ) -> Result<Self, ExportBoundaryError> {
        let binding = Self {
            workspace_id: workspace_id.into(),
            principal_id: principal_id.into(),
            principal_type: "user".to_string(),
            export_id: "legacy-export".to_string(),
            artifact_id: "legacy-artifact".to_string(),
            revision_id: "legacy-revision".to_string(),
            format: "json".to_string(),
        };
        if !is_bounded_id(&binding.workspace_id) || !is_bounded_id(&binding.principal_id) {
            return Err(ExportBoundaryError::permission_denied());
        }
        Ok(binding)
    }

    pub fn authorized(
        workspace_id: impl Into<String>,
        principal_id: impl Into<String>,
        principal_type: impl Into<String>,
        export_id: impl Into<String>,
        artifact_id: impl Into<String>,
        revision_id: impl Into<String>,
        format: impl Into<String>,
    ) -> Result<Self, ExportBoundaryError> {
        let binding = Self {
            workspace_id: workspace_id.into(),
            principal_id: principal_id.into(),
            principal_type: principal_type.into(),
            export_id: export_id.into(),
            artifact_id: artifact_id.into(),
            revision_id: revision_id.into(),
            format: format.into(),
        };
        if !is_bounded_id(&binding.workspace_id)
            || !is_bounded_id(&binding.principal_id)
            || binding.principal_type != "user"
            || !is_bounded_id(&binding.export_id)
            || !is_bounded_id(&binding.artifact_id)
            || !is_bounded_id(&binding.revision_id)
            || binding.format.is_empty()
            || binding.format.len() > 32
        {
            return Err(ExportBoundaryError::permission_denied());
        }
        Ok(binding)
    }

    pub fn export_id(&self) -> &str {
        &self.export_id
    }

    fn same_actor(&self, other: &Self) -> bool {
        self.workspace_id == other.workspace_id && self.principal_id == other.principal_id
    }
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct IssuedExportTicket {
    pub ticket: String,
    pub expires_in_ms: u64,
    pub max_bytes: usize,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct ArtifactExportResult {
    pub basename: String,
    pub sha256: String,
    pub size_bytes: usize,
    #[serde(skip_serializing)]
    pub binding: ExportBinding,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct ArtifactExportCancelResult {
    pub cancelled: bool,
    #[serde(skip_serializing)]
    pub binding: ExportBinding,
}

#[derive(Debug, Clone, Serialize, PartialEq, Eq)]
#[serde(rename_all = "camelCase")]
pub struct ExportBoundaryError {
    pub code: String,
    pub message: String,
    pub retryable: bool,
}

impl ExportBoundaryError {
    fn new(code: &str, message: &str, retryable: bool) -> Self {
        Self {
            code: code.to_string(),
            message: message.to_string(),
            retryable,
        }
    }

    fn permission_denied() -> Self {
        Self::new(
            "ARTIFACT_PERMISSION_DENIED",
            "artifact export ticket binding is invalid",
            false,
        )
    }

    fn cancelled() -> Self {
        Self::new(
            "ARTIFACT_EXPORT_CANCELLED",
            "artifact export ticket is missing, expired, or already consumed",
            false,
        )
    }

    fn failed(message: &str, retryable: bool) -> Self {
        Self::new("ARTIFACT_EXPORT_FAILED", message, retryable)
    }
}

struct ExportTicketRecord {
    target: PathBuf,
    binding: ExportBinding,
    max_bytes: usize,
    expires_at: Instant,
}

#[derive(Default)]
pub struct ArtifactExportState {
    tickets: Mutex<HashMap<String, ExportTicketRecord>>,
}

impl ArtifactExportState {
    pub async fn binding_for_ticket(
        &self,
        ticket: &str,
        binding: &ExportBinding,
    ) -> Result<ExportBinding, ExportBoundaryError> {
        let mut tickets = self.tickets.lock().await;
        let record = tickets
            .get(ticket)
            .ok_or_else(ExportBoundaryError::cancelled)?;
        if !record.binding.same_actor(binding) {
            return Err(ExportBoundaryError::permission_denied());
        }
        if record.expires_at <= Instant::now() {
            tickets.remove(ticket);
            return Err(ExportBoundaryError::cancelled());
        }
        Ok(record.binding.clone())
    }

    pub async fn issue_ticket(
        &self,
        target: PathBuf,
        binding: ExportBinding,
        max_bytes: usize,
        ttl: Duration,
    ) -> Result<IssuedExportTicket, ExportBoundaryError> {
        if max_bytes == 0
            || max_bytes > DEFAULT_MAX_EXPORT_BYTES
            || ttl.is_zero()
            || ttl > MAX_TICKET_TTL
            || target.file_name().is_none()
            || !matches!(target.parent(), Some(parent) if parent.is_dir())
        {
            return Err(ExportBoundaryError::failed(
                "artifact export target or boundary is invalid",
                false,
            ));
        }
        let ticket = format!("export-{}", Uuid::new_v4().simple());
        self.tickets.lock().await.insert(
            ticket.clone(),
            ExportTicketRecord {
                target,
                binding,
                max_bytes,
                expires_at: Instant::now() + ttl,
            },
        );
        Ok(IssuedExportTicket {
            ticket,
            expires_in_ms: ttl.as_millis() as u64,
            max_bytes,
        })
    }

    pub async fn commit(
        &self,
        ticket: &str,
        binding: &ExportBinding,
        bytes: Vec<u8>,
        expected_sha256: &str,
    ) -> Result<ArtifactExportResult, ExportBoundaryError> {
        let record = self.take_ticket(ticket, binding).await?;
        if bytes.len() > record.max_bytes {
            return Err(ExportBoundaryError::failed(
                "artifact export exceeds its ticket size boundary",
                false,
            ));
        }
        if expected_sha256.len() != 64
            || !expected_sha256
                .bytes()
                .all(|byte| byte.is_ascii_digit() || (b'a'..=b'f').contains(&byte))
        {
            return Err(ExportBoundaryError::failed(
                "artifact export hash is invalid",
                false,
            ));
        }
        let observed_sha256 = format!("{:x}", Sha256::digest(&bytes));
        if observed_sha256 != expected_sha256 {
            return Err(ExportBoundaryError::failed(
                "artifact export hash does not match",
                false,
            ));
        }
        let target = record.target;
        let result_binding = record.binding;
        let basename = target
            .file_name()
            .and_then(|value| value.to_str())
            .ok_or_else(|| ExportBoundaryError::failed("export basename is invalid", false))?
            .to_string();
        let ticket_owned = ticket.to_string();
        let size_bytes = bytes.len();
        tokio::task::spawn_blocking(move || atomic_write(&target, &ticket_owned, &bytes))
            .await
            .map_err(|_| {
                ExportBoundaryError::failed("artifact export write task failed", true)
            })??;
        Ok(ArtifactExportResult {
            basename,
            sha256: observed_sha256,
            size_bytes,
            binding: result_binding,
        })
    }

    pub async fn cancel(
        &self,
        ticket: &str,
        binding: &ExportBinding,
    ) -> Result<ArtifactExportCancelResult, ExportBoundaryError> {
        let record = self.take_ticket(ticket, binding).await?;
        Ok(ArtifactExportCancelResult { cancelled: true, binding: record.binding })
    }

    async fn take_ticket(
        &self,
        ticket: &str,
        binding: &ExportBinding,
    ) -> Result<ExportTicketRecord, ExportBoundaryError> {
        let mut tickets = self.tickets.lock().await;
        let record = tickets
            .get(ticket)
            .ok_or_else(ExportBoundaryError::cancelled)?;
        if !record.binding.same_actor(binding) {
            return Err(ExportBoundaryError::permission_denied());
        }
        if record.expires_at <= Instant::now() {
            tickets.remove(ticket);
            return Err(ExportBoundaryError::cancelled());
        }
        tickets
            .remove(ticket)
            .ok_or_else(ExportBoundaryError::cancelled)
    }
}

fn atomic_write(target: &Path, ticket: &str, bytes: &[u8]) -> Result<(), ExportBoundaryError> {
    let basename = target
        .file_name()
        .and_then(|value| value.to_str())
        .ok_or_else(|| ExportBoundaryError::failed("export basename is invalid", false))?;
    let temp_path = target.with_file_name(format!(".{basename}.{ticket}.tmp"));
    let mut created_by_us = false;
    let write_result = (|| -> std::io::Result<()> {
        let mut temp = OpenOptions::new()
            .create_new(true)
            .write(true)
            .open(&temp_path)?;
        created_by_us = true;
        temp.write_all(bytes)?;
        temp.sync_all()?;
        drop(temp);
        atomic_replace(&temp_path, target)
    })();
    if write_result.is_err() {
        if created_by_us {
            let _ = fs::remove_file(&temp_path);
        }
        return Err(ExportBoundaryError::failed(
            "artifact export could not be committed atomically",
            true,
        ));
    }
    Ok(())
}

#[cfg(not(windows))]
fn atomic_replace(temp_path: &Path, target: &Path) -> std::io::Result<()> {
    fs::rename(temp_path, target)?;
    if let Some(parent) = target.parent() {
        File::open(parent)?.sync_all()?;
    }
    Ok(())
}

#[cfg(windows)]
fn atomic_replace(temp_path: &Path, target: &Path) -> std::io::Result<()> {
    use std::os::windows::ffi::OsStrExt;
    use windows_sys::Win32::Storage::FileSystem::{
        MoveFileExW, MOVEFILE_REPLACE_EXISTING, MOVEFILE_WRITE_THROUGH,
    };

    let from = temp_path
        .as_os_str()
        .encode_wide()
        .chain(std::iter::once(0))
        .collect::<Vec<_>>();
    let to = target
        .as_os_str()
        .encode_wide()
        .chain(std::iter::once(0))
        .collect::<Vec<_>>();
    // SAFETY: both buffers are owned, NUL-terminated UTF-16 paths and remain
    // alive for the duration of the synchronous Windows API call.
    let result = unsafe {
        MoveFileExW(
            from.as_ptr(),
            to.as_ptr(),
            MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH,
        )
    };
    if result == 0 {
        return Err(std::io::Error::last_os_error());
    }
    Ok(())
}

fn is_bounded_id(value: &str) -> bool {
    if value.is_empty() || value.len() > 128 {
        return false;
    }
    let mut characters = value.chars();
    let Some(first) = characters.next() else {
        return false;
    };
    first.is_ascii_alphanumeric()
        && characters.all(|character| {
            character.is_ascii_alphanumeric() || matches!(character, '.' | '_' | '-')
        })
}

#[cfg(test)]
mod tests {
    use super::*;
    use sha2::{Digest, Sha256};
    use std::time::Duration;

    fn binding(principal: &str) -> ExportBinding {
        ExportBinding::new("workspace-1", principal).expect("binding should validate")
    }

    #[test]
    fn ticket_is_principal_bound_single_use_and_path_opaque() {
        let runtime = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .expect("runtime");
        runtime.block_on(async {
            let state = ArtifactExportState::default();
            let root = tempfile::tempdir().expect("tempdir");
            let issued = state
                .issue_ticket(
                    root.path().join("report.json"),
                    binding("user-1"),
                    1024,
                    Duration::from_secs(60),
                )
                .await
                .expect("ticket");
            let serialized = serde_json::to_string(&issued).expect("serialize");

            assert!(!serialized.contains(root.path().to_string_lossy().as_ref()));
            assert!(state
                .cancel(&issued.ticket, &binding("user-2"))
                .await
                .is_err());
            assert!(state
                .cancel(&issued.ticket, &binding("user-1"))
                .await
                .is_ok());
            assert!(state
                .cancel(&issued.ticket, &binding("user-1"))
                .await
                .is_err());
        });
    }

    #[test]
    fn authorized_ticket_retains_exact_revision_binding_without_renderer_leakage() {
        let runtime = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .expect("runtime");
        runtime.block_on(async {
            let state = ArtifactExportState::default();
            let root = tempfile::tempdir().expect("tempdir");
            let exact = ExportBinding::authorized(
                "workspace-1", "user-1", "user", "export-1", "artifact-1",
                "revision-7", "source",
            ).expect("authorized binding");
            let issued = state.issue_ticket(
                root.path().join("main.py"), exact.clone(), 1024, Duration::from_secs(60),
            ).await.expect("ticket");

            let observed = state.binding_for_ticket(&issued.ticket, &binding("user-1"))
                .await.expect("binding lookup");
            assert_eq!(observed, exact);
            let cancelled = state.cancel(&issued.ticket, &binding("user-1"))
                .await.expect("cancel");
            let serialized = serde_json::to_string(&cancelled).expect("serialize");
            assert!(!serialized.contains("revision-7"));
            assert!(!serialized.contains("export-1"));
        });
    }

    #[test]
    fn commit_checks_hash_size_and_leaves_no_partial_file() {
        let runtime = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .expect("runtime");
        runtime.block_on(async {
            let state = ArtifactExportState::default();
            let root = tempfile::tempdir().expect("tempdir");
            let target = root.path().join("report.json");
            let bytes = br#"{"status":"ok"}"#.to_vec();
            let digest = format!("{:x}", Sha256::digest(&bytes));
            let issued = state
                .issue_ticket(
                    target.clone(),
                    binding("user-1"),
                    1024,
                    Duration::from_secs(60),
                )
                .await
                .expect("ticket");
            let result = state
                .commit(&issued.ticket, &binding("user-1"), bytes.clone(), &digest)
                .await
                .expect("commit");

            assert_eq!(std::fs::read(&target).expect("target"), bytes);
            assert_eq!(result.sha256, digest);
            assert_eq!(result.size_bytes, 15);
            assert!(state
                .commit(&issued.ticket, &binding("user-1"), Vec::new(), &digest)
                .await
                .is_err());
            assert_eq!(
                std::fs::read_dir(root.path()).expect("dir").count(),
                1,
                "no temp file may remain"
            );
        });
    }

    #[test]
    fn failed_create_does_not_delete_a_preexisting_temp_file() {
        let runtime = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .expect("runtime");
        runtime.block_on(async {
            let state = ArtifactExportState::default();
            let root = tempfile::tempdir().expect("tempdir");
            let target = root.path().join("report.json");
            let bytes = b"safe export".to_vec();
            let digest = format!("{:x}", Sha256::digest(&bytes));
            let issued = state
                .issue_ticket(
                    target.clone(),
                    binding("user-1"),
                    1024,
                    Duration::from_secs(60),
                )
                .await
                .expect("ticket");
            let temp = root
                .path()
                .join(format!(".report.json.{}.tmp", issued.ticket));
            std::fs::write(&temp, b"not ours").expect("seed collision");

            let error = state
                .commit(&issued.ticket, &binding("user-1"), bytes, &digest)
                .await
                .expect_err("create_new collision must fail closed");

            assert_eq!(error.code, "ARTIFACT_EXPORT_FAILED");
            assert_eq!(
                std::fs::read(&temp).expect("collision survives"),
                b"not ours"
            );
            assert!(!target.exists());
        });
    }

    #[test]
    fn expired_and_oversized_tickets_fail_without_output() {
        let runtime = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .expect("runtime");
        runtime.block_on(async {
            let state = ArtifactExportState::default();
            let root = tempfile::tempdir().expect("tempdir");
            let expired_target = root.path().join("expired.json");
            let expired = state
                .issue_ticket(
                    expired_target.clone(),
                    binding("user-1"),
                    16,
                    Duration::from_millis(1),
                )
                .await
                .expect("ticket");
            tokio::time::sleep(Duration::from_millis(5)).await;
            let empty_digest = format!("{:x}", Sha256::digest([]));
            let expired_error = state
                .commit(
                    &expired.ticket,
                    &binding("user-1"),
                    Vec::new(),
                    &empty_digest,
                )
                .await
                .expect_err("expired ticket");
            assert_eq!(expired_error.code, "ARTIFACT_EXPORT_CANCELLED");
            assert!(!expired_target.exists());

            let oversized_target = root.path().join("oversized.json");
            let oversized = state
                .issue_ticket(
                    oversized_target.clone(),
                    binding("user-1"),
                    3,
                    Duration::from_secs(60),
                )
                .await
                .expect("ticket");
            let bytes = b"four".to_vec();
            let digest = format!("{:x}", Sha256::digest(&bytes));
            let size_error = state
                .commit(&oversized.ticket, &binding("user-1"), bytes, &digest)
                .await
                .expect_err("size boundary");
            assert_eq!(size_error.code, "ARTIFACT_EXPORT_FAILED");
            assert!(!oversized_target.exists());
        });
    }
}
