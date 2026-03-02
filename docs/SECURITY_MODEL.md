# SECURITY_MODEL (v0.3)

## Default Posture

- Web access disabled by default
- Privacy mode enabled by default
- Persistent traces only when debug is on and privacy is explicitly disabled
- Tool execution constrained by allowlist + sandbox runner
- Governance policy defaults to fail-closed for execution commands

## Tool Allowlist

Allowed command roots:

- `python`
- `uv`
- `pytest`
- `ruff`
- `rg`

Commands outside allowlist are rejected with deterministic error (`exit_code=126`).

## Runtime Guardrails

- `max_tool_calls` enforced per request
- `max_recursion_depth` enforced per session context
- expert timeout + retry limits
- circuit breaker cooldown for repeated expert failures
- task/tool policy evaluation (`allow|deny|require_approval`)
- async approval queue with audit trail

## Prompt/Tool Injection Defense

- Planner output must validate strict schema
- Invalid planner output triggers deterministic fallback reason code
- Document content is treated as content, never as executable shell command
- Tool runner only accepts explicit allowlisted command arrays
- Tool commands are policy-evaluated on canonicalized command/arg form
