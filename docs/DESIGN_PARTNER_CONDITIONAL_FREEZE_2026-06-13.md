# Design Partner Conditional Freeze - 2026-06-13

The design partner pilot candidate is frozen as conditional on 2026-06-13.

This closure means the local rehearsal, provider governance, provider workflow
proof, operator panel, control-plane, and pilot candidate gates are green with
no blockers. It does not mean the strict design partner RC is ready.

Strict RC promotion remains blocked by missing real target-environment evidence
and independent operator attestation. Rehearsal evidence must stay labeled as
rehearsal-only and must not be used as target-environment proof.

Boundary claims remain unchanged:

- Public desktop installer: blocked.
- Unrestricted live computer-use: blocked.
- Approval-free irreversible mutation: blocked.
- Multi-tenant cloud control plane: deferred.

Promotion path:

1. Run a real target-environment design partner evidence session.
2. Collect independent operator attestation for that session.
3. Rerun the strict RC gate.
4. Promote conditional to ready only when the strict gate passes with
   `blockers=[]` and target evidence verified as real target-environment
   evidence.
