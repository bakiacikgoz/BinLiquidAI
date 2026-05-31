# Agent Control Plane Demo Runbook

1. Register the governed ops agent.
2. Simulate policy decisions.
3. Submit a governed run.
4. Inspect the approval-required result.
5. Export the evidence pack.
6. Verify the evidence manifest.
7. Verify the claim matrix.

```bash
uv run binliquid control-plane agent register --spec examples/control_plane/agent_governed_ops.yaml --profile enterprise --json
uv run binliquid control-plane policy simulate --agent-id governed-ops --profile enterprise --json
uv run binliquid control-plane run submit --agent-id governed-ops --once "Inspect queue and draft remediation" --profile enterprise --json
uv run binliquid control-plane claims verify --profile enterprise --json
```

For a deterministic local summary:

```bash
uv run python scripts/run_control_plane_demo.py --profile enterprise --json
```
