# Design Partner Pilot Candidate Handoff

The pilot candidate pack assembles RC status, target evidence closure, optional
operator attestation, provider workflow proof, claim guard output, and handoff
documents into a single review folder.

Generate the pack:

```bash
make design-partner-pilot-candidate-gate
```

Direct script:

```bash
uv run python scripts/generate_design_partner_pilot_candidate_pack.py \
  --profile enterprise \
  --target-evidence-root artifacts/design-partner-target-evidence \
  --rc-root artifacts/design-partner-rc \
  --output-root artifacts/design-partner-pilot-candidate \
  --json
```

Status semantics:

- `pass`: target evidence, attestation, RC status, claim guard, and provider
  workflow proof are complete with no warnings.
- `conditional`: no blocker exists, but rehearsal-only target evidence or missing
  optional review material remains.
- `blocked`: raw persistence, secret persistence, hash mismatch, opened public/live
  boundary, invalid target evidence, or blocked RC status exists.

The pack does not claim public desktop availability, unrestricted live
computer-use, multi-tenant SaaS readiness, or approval-free irreversible
mutation.
