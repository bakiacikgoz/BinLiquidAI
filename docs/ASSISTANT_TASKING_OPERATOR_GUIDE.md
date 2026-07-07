# Assistant Tasking Operator Guide

Use assistant tasking when an operator wants an enrolled external agent to do a
governed task.

1. Ask for a plan. The assistant shows selected agent, risk, policy preview,
   approval requirement, idempotency key, and expected evidence refs.
2. Check the status. `planned` means the task is a proposal, not an execution.
3. Submit only when the UI or CLI sends the exact `planHash` as `confirmPlanHash`.
4. Inspect the result:
   - `accepted`: read-only task was accepted and includes `runId` plus `evidenceRef`.
   - `blocked_pending_approval`: write task needs approval and includes `approvalId`.
   - `denied`: task was not sent to the gateway.
   - `invalid_request`: confirmation, schema, or idempotency failed.
5. Use `assistant task explain` to see source docs, policy, and evidence refs.

Do not override these blockers:

- `ASSISTANT_TASK_DESTRUCTIVE_DENIED`
- `ASSISTANT_TASK_UNENROLLED_AGENT_DENIED`
- `ASSISTANT_TASK_UNKNOWN_AGENT_DENIED`
- `ASSISTANT_TASK_PROMPT_INJECTION_DENIED`
- `ASSISTANT_TASK_RAW_SECRET_LEAK`

If a task is blocked, fix the root cause: enroll the agent, choose a safer task,
request approval, or remove sensitive input.
