# AI Assistant Operator Guide

Use AegisOS Assistant for read-only explanation, troubleshooting, and governed plan drafting.
It can cite local docs, contracts, run context, approvals, and evidence. It must not execute
mutating work by itself.

For platform usage questions, expect the answer to include source paths such as:

- `docs/AI_ASSISTANT_SYSTEM_KNOWLEDGE.md`
- `docs/EXTERNAL_AGENT_GATEWAY_GUIDE.md`
- `docs/AGENT_CONTROL_PLANE_ADAPTER_CONTRACT.md`

For setup issues, run:

```bash
uv run binliquid assistant doctor --profile enterprise --json
uv run binliquid assistant knowledge doctor --profile enterprise --json
```
