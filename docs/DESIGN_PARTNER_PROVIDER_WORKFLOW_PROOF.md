# Design Partner Provider Workflow Proof

The first provider-governed workflow proof is read-only IT/ops triage.

Input:

```text
Inspect service alerts and draft remediation plan
```

Expected behavior:

- read-only context is inspected by policy simulation and provider dry-run
  invocation
- provider invocation writes hash-only evidence
- remediation suggestions are represented as proposals
- mutating suggestions such as `restart-service` stay `proposal_only`
- `executedMutations=0`
- at least one approval ticket proposal is represented
- Operator Panel shows Provider Trust, Provider Execution Evidence, and
  Workflow Proof without raw JSON as primary content

Verification:

```bash
make provider-workflow-proof-gate
corepack pnpm --dir apps/operator-panel test:e2e -- provider-workflow-proof.spec.ts
```
