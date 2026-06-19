# Windows Gate Troubleshooting

## `make` Is Not Installed

Windows developer shells may not include `make`. This is not a release blocker. Use the direct Python gate:

```powershell
uv run python scripts/run_enterprise_workspace_release_closure_gate.py --profile enterprise --json
```

## `uv run pytest` Canonicalization

If a command such as this fails:

```powershell
uv run --extra dev pytest -q
```

run pytest through the active interpreter instead:

```powershell
uv run python -m pytest -q
```

or:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

The release closure gate uses interpreter-module pytest mode to avoid the script shim path issue.

## Tauri Permission Path Failure

If this fails under OneDrive or a Unicode path:

```powershell
cargo test -q --manifest-path apps/operator-panel/src-tauri/Cargo.toml
```

use the stable target-dir command:

```powershell
cargo test -q --manifest-path apps/operator-panel/src-tauri/Cargo.toml --target-dir apps/operator-panel/src-tauri/target-codex-test
```

The closure gate uses this stable command as the required Tauri validation path. The default-target command may still be recorded as a diagnostic when it fails.
