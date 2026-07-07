# Assistant Governed Tasking

Assistant governed tasking turns an operator message into a proposal-first agent task.
It does not let the assistant execute directly from model text.

Core rules:

- A task must have an `AssistantTaskPlan` before submission.
- Submission requires `confirmPlanHash` and `operatorId`.
- Read-only external gateway tasks can be accepted after confirmation.
- External write tasks return `blocked_pending_approval` with an `approvalId`.
- Destructive, credential-sensitive, prompt-injection, unknown-agent, unenrolled-agent,
  and cross-workspace tasks stay denied.
- Artifacts are hash-only/redacted. Raw prompts, provider payloads, tokens, and secrets
  are not persisted.
- Live computer-use is not enabled by this surface.

Primary CLI:

```bash
uv run binliquid assistant task plan --message "Governed ops agent'e son servis uyarilarini incele." --json
uv run binliquid assistant task submit --proposal-id <proposal-id> --confirm-plan-hash <plan-hash> --operator-id operator-local --json
uv run binliquid assistant task status --proposal-id <proposal-id> --json
uv run binliquid assistant task explain --proposal-id <proposal-id> --json
```

Release proof:

```bash
uv run python scripts/run_assistant_governed_tasking_gate.py --profile enterprise --json
```
