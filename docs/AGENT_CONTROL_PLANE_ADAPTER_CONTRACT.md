# Agent Control Plane Adapter Contract

The first external integration surface is stdio/JSON. No local HTTP listener is
enabled by default.

External frameworks submit an action proposal with:

- `agent_id`
- `run_id`
- `action_id`
- `risk_class`
- `target_kind`
- `effect_summary`
- `idempotency_key`

The Control Plane returns a policy decision with `allow`, `require_approval` or
`deny`. Invalid JSON, missing risk class, unknown event type or malformed
payloads fail closed as `ADAPTER_CONTRACT_INVALID`.

LangGraph, CrewAI and OpenAI Agents SDK wrappers are out of scope for this v1
slice and should be added only after a pilot integration requires them.
