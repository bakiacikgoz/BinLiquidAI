# External Agent Gateway Guide

Register the sample external stdio agent:

```bash
uv run binliquid control-plane agent register \
  --spec examples/control_plane/agent_external_gateway.yaml \
  --profile lite \
  --json
```

Submit governed requests with `control-plane gateway submit-action --input <json>`.
Read-only requests can be accepted. External writes require approval. Destructive
and credential-sensitive requests are denied by default.

Contract fixtures live in `contracts/control_plane/fixtures/external_agent_*.json`.

