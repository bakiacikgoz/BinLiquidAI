# Operator Attestation Runbook

Operator attestation records that a human reviewed the target evidence boundary
without storing the operator name in clear text.

Generate an attestation after a session exists:

```bash
uv run python scripts/generate_operator_attestation.py \
  --session artifacts/design-partner-target-evidence/session.json \
  --operator-display-name local-operator \
  --output-root artifacts/design-partner-target-evidence \
  --json
```

`make operator-attestation-gate` checks the schema and verifies that all required
public/live boundaries are accepted as blocked.

Rules:

- `operatorDisplayNameHash` is sha256 metadata only.
- `acceptedBoundaries` must include the public desktop and live computer-use
  blocked claims.
- The absence of signing is acceptable for local rehearsal, but it remains
  visible as attestation status rather than being promoted to a signed claim.
- Operator Panel shows attestation state in the primary UI without raw JSON.
