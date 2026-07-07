# Source Install RC Handoff

The source install RC claim set is limited to source/local installation evidence.
It does not cover signed public desktop installers, SaaS, or unrestricted live
computer-use.

## Build Claim

```bash
uv run binliquid local-product source-install claim --profile enterprise --json
```

The claim output lists:

- `claimedTargets`: targets with verified current-commit evidence.
- `notEvidencedTargets`: targets that must not be claimed yet.
- `releaseNotesAllowedClaims`: release-note-safe target claims.
- `noShipBlockers`: blockers if a requested target lacks evidence or is stale.

## Missing Target Actions

```bash
uv run binliquid local-product target actions --profile enterprise --json
```

Use these actions to collect missing target bundles before broadening release
claims.

