use base64::{engine::general_purpose::STANDARD, Engine};
use portable_pty::{native_pty_system, CommandBuilder, PtySize};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::io::Write;
use std::path::PathBuf;
use std::sync::Mutex;
use tauri::{AppHandle, Emitter, State};

#[derive(Default)]
pub struct TerminalManager {
    sessions: Mutex<HashMap<String, TerminalSession>>,
}

struct TerminalSession {
    writer: Box<dyn Write + Send>,
    master: Box<dyn portable_pty::MasterPty + Send>,
    child: Box<dyn portable_pty::Child + Send>,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct TerminalStartRequest {
    pub mode: String,
    pub cwd: Option<String>,
    pub cols: u16,
    pub rows: u16,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct TerminalWriteRequest {
    pub session_id: String,
    pub data: String,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct TerminalResizeRequest {
    pub session_id: String,
    pub cols: u16,
    pub rows: u16,
}

#[derive(Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct TerminalKillRequest {
    pub session_id: String,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
pub struct TerminalStartResponse {
    pub session_id: String,
    pub shell: String,
}

fn terminal_error(message: &str) -> String {
    format!("TERMINAL_DENIED: {message}")
}

fn shell_command() -> Result<CommandBuilder, String> {
    #[cfg(target_os = "windows")]
    {
        Ok(CommandBuilder::new("powershell.exe"))
    }
    #[cfg(not(target_os = "windows"))]
    {
        Ok(CommandBuilder::new("/bin/zsh"))
    }
}

fn safe_cwd(value: Option<String>) -> Result<Option<PathBuf>, String> {
    let Some(value) = value else { return Ok(None) };
    let path = PathBuf::from(value);
    if !path.is_absolute() || !path.is_dir() {
        return Err(terminal_error(
            "working directory must be an existing absolute directory",
        ));
    }
    Ok(Some(path))
}

#[tauri::command]
pub fn terminal_start(
    app: AppHandle,
    state: State<'_, TerminalManager>,
    request: TerminalStartRequest,
) -> Result<TerminalStartResponse, String> {
    if request.mode != "user" {
        return Err(terminal_error(
            "only user-started terminal sessions are enabled",
        ));
    }
    if request.cols == 0 || request.rows == 0 || request.cols > 500 || request.rows > 300 {
        return Err(terminal_error("terminal dimensions are outside policy"));
    }
    let mut command = shell_command()?;
    if let Some(cwd) = safe_cwd(request.cwd)? {
        command.cwd(cwd);
    }
    let pair = native_pty_system()
        .openpty(PtySize {
            rows: request.rows,
            cols: request.cols,
            pixel_width: 0,
            pixel_height: 0,
        })
        .map_err(|_| terminal_error("could not allocate PTY"))?;
    let child = pair
        .slave
        .spawn_command(command)
        .map_err(|_| terminal_error("could not start terminal shell"))?;
    let reader = pair
        .master
        .try_clone_reader()
        .map_err(|_| terminal_error("could not read PTY"))?;
    let writer = pair
        .master
        .take_writer()
        .map_err(|_| terminal_error("could not write PTY"))?;
    let session_id = format!("terminal-{}", uuid::Uuid::new_v4());
    let event_id = session_id.clone();
    std::thread::spawn(move || {
        use std::io::Read;
        let mut reader = reader;
        let mut buffer = [0_u8; 4096];
        while let Ok(count) = reader.read(&mut buffer) {
            if count == 0 {
                break;
            }
            let _ = app.emit("terminal://output", serde_json::json!({"sessionId": event_id, "data": STANDARD.encode(&buffer[..count])}));
        }
    });
    state
        .sessions
        .lock()
        .map_err(|_| terminal_error("terminal manager unavailable"))?
        .insert(
            session_id.clone(),
            TerminalSession {
                writer,
                master: pair.master,
                child,
            },
        );
    Ok(TerminalStartResponse {
        session_id,
        shell: if cfg!(windows) {
            "powershell.exe".into()
        } else {
            "/bin/zsh".into()
        },
    })
}

#[tauri::command]
pub fn terminal_write(
    state: State<'_, TerminalManager>,
    request: TerminalWriteRequest,
) -> Result<(), String> {
    let mut sessions = state
        .sessions
        .lock()
        .map_err(|_| terminal_error("terminal manager unavailable"))?;
    let session = sessions
        .get_mut(&request.session_id)
        .ok_or_else(|| terminal_error("unknown terminal session"))?;
    session
        .writer
        .write_all(request.data.as_bytes())
        .map_err(|_| terminal_error("terminal write failed"))
}

#[tauri::command]
pub fn terminal_resize(
    state: State<'_, TerminalManager>,
    request: TerminalResizeRequest,
) -> Result<(), String> {
    if request.cols == 0 || request.rows == 0 || request.cols > 500 || request.rows > 300 {
        return Err(terminal_error("terminal dimensions are outside policy"));
    }
    let sessions = state
        .sessions
        .lock()
        .map_err(|_| terminal_error("terminal manager unavailable"))?;
    let session = sessions
        .get(&request.session_id)
        .ok_or_else(|| terminal_error("unknown terminal session"))?;
    session
        .master
        .resize(PtySize {
            rows: request.rows,
            cols: request.cols,
            pixel_width: 0,
            pixel_height: 0,
        })
        .map_err(|_| terminal_error("terminal resize failed"))
}

#[tauri::command]
pub fn terminal_kill(
    state: State<'_, TerminalManager>,
    request: TerminalKillRequest,
) -> Result<(), String> {
    let mut sessions = state
        .sessions
        .lock()
        .map_err(|_| terminal_error("terminal manager unavailable"))?;
    let mut session = sessions
        .remove(&request.session_id)
        .ok_or_else(|| terminal_error("unknown terminal session"))?;
    session
        .child
        .kill()
        .map_err(|_| terminal_error("terminal kill failed"))
}
