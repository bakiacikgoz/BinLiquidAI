# Windows Tauri Target Dir Guide

Use an explicit target directory for stable Windows and OneDrive-adjacent test
paths:

```powershell
cargo test -q --manifest-path apps/operator-panel/src-tauri/Cargo.toml --target-dir apps/operator-panel/src-tauri/target-codex-test
```

The explicit target-dir path is the product-complete validation path.
