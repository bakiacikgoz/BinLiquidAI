# Non-Developer Operator Attestation

## Purpose

This document defines the final human sign-off step after the automated
operator validation drill passes.

The attestation must be completed by an operator who is not the developer who
implemented the release changes. Automated proxy validation is useful evidence,
but it is not a substitute for this attestation.

## Who Can Attest

The attesting operator must:

- be independent from the implementation work being validated;
- review `docs/OPERATIONS_RUNBOOK.md`;
- review the latest `operator_validation_report.json`;
- confirm the release pack path being attested;
- complete the attestation JSON from the template below.

Codex, the implementation developer, or any automated test may prepare the
template and verify the file format, but must not fill in or claim the human
attestation.

## Template

Copy:

```text
docs/templates/non_developer_operator_attestation.template.json
```

to an evidence path outside git, for example:

```text
artifacts/readiness/2026-05-13/operator_validation_attestation.json
```

Then replace every placeholder with real operator-provided values. Keep
`non_developer_operator`, `reviewed_runbook`, and `completed_validation` set to
`true` only if the operator actually completed those checks.

## Validation Command

Run the drill with the attestation file:

```bash
uv run python scripts/run_operator_validation_drill.py \
  --output-root artifacts/readiness/2026-05-13/operator_validation_drill_attested \
  --operator-attestation artifacts/readiness/2026-05-13/operator_validation_attestation.json
```

The report may claim `validation_scope=non_developer_operator_attested` only
when:

- all command checks pass;
- all evidence checks pass;
- the attestation file is valid JSON;
- `schema_version` is
  `binliquid-non-developer-operator-attestation/v1`;
- required operator fields are non-empty;
- `signed_at_utc` is a valid UTC timestamp ending in `Z`;
- the attestation booleans are explicitly `true`.

If no attestation is provided, the drill remains valid only as
`operator_proxy_dry_run`.
