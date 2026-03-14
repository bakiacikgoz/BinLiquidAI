# Operator Contract Behavior

## Versioning

- Operator bridge payloads use `contractVersion="2.0"` in camelCase.
- CLI JSON payloads and team artifact files use `contract_version="2.0"` in snake_case.
- Stream events remain versioned by `schema_version="3"`.
- Audit envelopes remain versioned by `contract_version="2.0"` plus `envelope_version="3"`, `event_schema_version="3"`, and `handoff_schema_version="3"`.

## Frozen Surfaces

- Capabilities: `operator capabilities --json`
- Bridge handshake and spawned submit/resume payloads
- Approval pending/detail payloads
- Team list/status/replay payloads
- Team artifacts: `status.json`, `tasks.json`, `handoffs.json`, `audit_envelope.json`
- Operations payloads surfaced in the operator workspace
- Computer-use device action approval snapshot

## Empty State Rules

- `team list` with no jobs returns `count=0`, `items=[]`, `errors=[]`.
- `approval pending` with no tickets returns `pending=[]`.
- `team status` preserves the frozen shape even when `tasks=[]`, `resume_outcomes=[]`, or `continuation={}`.
- Operations commands must keep `contract_version` even when the payload is an empty verification result (`checks={}`, `errors=[]`).
- Preview mode must return the same contract shape as runtime; preview-only wrappers are not allowed on flow payloads.

## Optional Field Rules

- Run summary uses `finished_at=""` when a listed job has not completed yet.
- Run detail/status artifact uses `finished_at=null` when the active run has not completed yet.
- Approval tickets may keep `executed_at`, `decided_at`, `consumed_at`, and resume claim fields as `null`.
- Signed artifact verification may keep `error_code=null` on success.

## Source Of Truth

- Contract schemas live under [contracts/operator_panel/schemas](/Users/baki/Desktop/lnn/contracts/operator_panel/schemas).
- Preview fixtures live in [operator_panel_preview.json](/Users/baki/Desktop/lnn/contracts/operator_panel/fixtures/operator_panel_preview.json).
- The schema generator is [generate_operator_contract_schemas.py](/Users/baki/Desktop/lnn/scripts/generate_operator_contract_schemas.py).
