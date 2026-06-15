# Model Provider Governance V1.1 PR Body

## Summary

- Closes provider governance V1.1 with offline conformance, release closure verification, and Operator Panel trust metadata.
- Adds Native Adapter V2 contract models and a disabled OpenAI Responses skeleton.
- Adds DeepSeek and Gemini-compatible disabled fixtures for conformance coverage.

## Safety

- Remote providers remain disabled by default.
- Live canary remains double opt-in and is not run in CI.
- Provider evidence persists hashes and metadata only.
- Router recommendations remain shadow-only.
- Native server-side tools are denied by default.

## Validation

```powershell
uv run --extra dev ruff check .
uv run --extra dev python -m pytest -q
uv run python scripts/run_provider_governance_gate.py --profile enterprise --json
uv run python scripts/generate_provider_conformance_matrix.py --profile enterprise --mode offline --output-root artifacts/model-provider-governance/conformance --json
uv run python scripts/verify_provider_release_closure.py --profile enterprise --evidence-root artifacts/model-provider-governance/v1_1 --json
corepack pnpm --dir apps/operator-panel test
corepack pnpm --dir apps/operator-panel lint
corepack pnpm --dir apps/operator-panel build
cargo test -q --manifest-path apps/operator-panel/src-tauri/Cargo.toml
git diff --check
```
