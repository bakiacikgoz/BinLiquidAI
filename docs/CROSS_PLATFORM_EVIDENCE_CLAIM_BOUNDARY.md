# Cross-Platform Evidence Claim Boundary

BinLiquid local product support claims are target-scoped. A passing run on one
host proves only the target that produced the evidence bundle.

## Allowed Claims

- `windows-x64 source/local install evidenced`
- `linux-x64 source/local install evidenced`
- `darwin-arm64 source/local install evidenced`
- `darwin-x64 source/local install evidenced`

These claims are allowed only when the current commit has imported, verified
evidence for the target.

## Disallowed Claims

- `all processors supported`
- `all macOS devices supported`
- `Windows, Linux, and macOS supported` when any listed target is not evidenced
- Any Apple Silicon claim based only on an Intel Mac run
- Any Intel Mac claim based only on an Apple Silicon run

## No-Ship Conditions

- `PLATFORM_CLAIM_WITHOUT_EVIDENCE`
- `PLATFORM_EVIDENCE_COMMIT_MISMATCH`
- `PLATFORM_EVIDENCE_TARGET_MISMATCH`
- `PLATFORM_EVIDENCE_SECRET_LEAK`
- `PLATFORM_EVIDENCE_STALE`
- `UNBOUNDED_PLATFORM_SUPPORT_CLAIM`

Targets that are in source support but lack imported evidence must remain
`not_evidenced`. They are not product failures unless release text claims them.
