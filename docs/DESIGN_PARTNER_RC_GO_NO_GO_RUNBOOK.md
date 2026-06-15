# Design Partner RC Go/No-Go Runbook

Run the official Windows-compatible gate:

```bash
uv run python scripts/run_rc_release_decision_gate.py --profile enterprise --json
```

Go conditions:

- RC gate ledger verifies ready.
- RC freeze missing-gate warnings are reconciled.
- No blocking no-ship item is open.
- Required human sign-off roles verify against the current dossier hash.

No-go conditions:

- Public desktop claim without Hat B evidence.
- Live Windows or Linux computer-use claim.
- Raw/secret marker or artifact hash mismatch.
- Missing or stale human sign-off for final approval.

Hat B external credential blockers do not block Hat A or Design Partner source/CLI RC discussion, but they block public desktop approval.
