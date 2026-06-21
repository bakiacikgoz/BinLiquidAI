# Desktop Installer Readiness

Internal desktop readiness uses build/test evidence, not a public signing claim.

Stable Tauri test path:

```bash
cargo test -q --manifest-path apps/operator-panel/src-tauri/Cargo.toml --target-dir apps/operator-panel/src-tauri/target-codex-test
```

Public signed installer claims require real certificate, signing, and
notarization evidence and remain outside local product-complete proof.
