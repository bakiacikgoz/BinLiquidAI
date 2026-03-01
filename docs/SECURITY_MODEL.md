# SECURITY_MODEL

## Default Security Posture

- Web access disabled by default
- Privacy mode enabled by default
- Persistent traces only when `--debug --privacy-off`
- Tool execution constrained by allowlist and sandbox runner

## Tool Allowlist

Allowed command roots:

- `python`
- `uv`
- `pytest`
- `ruff`
- `rg`

Commands outside allowlist are rejected with deterministic error code.

## Runtime Guardrails

- `max_tool_calls` enforced per request
- `max_recursion_depth` enforced via session context
- Expert timeout and retry limits enforced by orchestrator
- Circuit breaker prevents repeated failing experts

## Injection Defense

- Planner output must validate strict schema
- Non-JSON planner output triggers deterministic fallback
- Tool execution does not interpret document text as shell commands
