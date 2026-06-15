# Model Provider Native Adapter V2 Closure Report

Status: completed as an offline vertical slice.

## Scope Delivered

- Added the `openai_responses` provider kind.
- Added OpenAI Responses native request and result contracts.
- Added generated schemas for native request, result, storage policy, tool policy decisions, tool proposals, and native conformance reports.
- Added an OpenAI Responses payload builder that forces `store=false`, disables parallel tool calls, and keeps raw content persistence off.
- Added response normalization for text output, structured JSON output, and custom function tool proposals.
- Added fail-closed handling for server-side tools, built-in tools, MCP tools, unsupported output blocks, storage override attempts, and secret-like output.
- Added offline conformance fixtures and a native adapter gate.
- Added CLI commands under `provider native conformance`.
- Added Operator Panel V3 trust metadata for the native preview provider.
- Added CI and Makefile integration for the native adapter gate.

## Default Runtime Boundary

- The native adapter remains disabled by default.
- The OpenAI Responses row is preview/canary-only.
- No production routing is enabled by this slice.
- No live canary is run by default.

## Conformance Result

Latest local native gate result:

- total cases: 11
- passing cases: 3
- expected-blocked cases: 8
- unexpected failures: 0
- live canary attempted: false
- evidence verification: pass

The expected-blocked cases cover unsafe or unsupported behavior, including server tools, MCP tools, storage override attempts, unknown output blocks, and secret-like output.

## Evidence Paths

- Native gate JSON: `artifacts/model-provider-governance/native-v2/provider_native_adapter_gate.json`
- Native conformance JSON: `artifacts/model-provider-governance/native-v2/native_adapter_gate_report.json`
- Native conformance Markdown: `artifacts/model-provider-governance/native-v2/native_adapter_gate_report.md`

## Required Validation Commands

```bash
uv run --extra dev ruff check .
uv run --extra dev python -m pytest -q
uv run python scripts/run_provider_governance_gate.py --profile enterprise --json
uv run python scripts/run_provider_native_adapter_gate.py --profile enterprise --json
corepack pnpm --dir apps/operator-panel test
corepack pnpm --dir apps/operator-panel lint
corepack pnpm --dir apps/operator-panel build
cargo test -q --manifest-path apps/operator-panel/src-tauri/Cargo.toml --target-dir apps/operator-panel/src-tauri/target-codex-test
git diff --check
```

## Non-Claims

- This slice does not certify live OpenAI Responses production routing.
- This slice does not enable provider-hosted tools.
- This slice does not execute custom function tool proposals.
- This slice does not approve Anthropic, Gemini, DeepSeek, or other native adapters.
