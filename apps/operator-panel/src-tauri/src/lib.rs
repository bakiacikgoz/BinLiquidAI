mod bridge;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_log::Builder::default().build())
        .invoke_handler(tauri::generate_handler![
            bridge::bridge_handshake,
            bridge::bridge_approval_pending,
            bridge::bridge_approval_show,
            bridge::bridge_approval_decide,
            bridge::bridge_approval_execute,
            bridge::bridge_team_list,
            bridge::bridge_team_replay,
            bridge::bridge_team_status,
            bridge::bridge_team_export,
            bridge::bridge_read_artifact,
            bridge::bridge_tail_events,
        ])
        .run(tauri::generate_context!())
        .expect("error while running operator panel");
}
