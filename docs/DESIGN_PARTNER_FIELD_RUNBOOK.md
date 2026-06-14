# Design Partner Field Runbook

This runbook is for the operator-assisted design-partner target environment
closure. It does not authorize public desktop release, live computer-use, or
destructive mutation.

## Steps

1. Run `make governed-pilot-workflow-gate`.
2. Prepare the target-environment field session with
   `--ack-target-environment`.
3. Collect field evidence from the local artifact root.
4. Verify the field evidence bundle.
5. Have an independent non-developer operator complete the attestation JSON.
6. Run `pilot field attest-verify`.
7. Run `pilot field promote-rc`.
8. Run `make design-partner-field-evidence-gate`.

## Operator Attestation

The operator must be independent from implementation work and must not use
placeholder values. The attestation must bind:

- `sessionId`;
- `targetEnvironmentLabelHash`;
- `bundleSha256`;
- `releasePackId`;
- explicit `nonDeveloperOperator`, `reviewedRunbook`, and
  `completedValidation` booleans.

## Stop Conditions

Stop and do not promote if any of these appear:

- raw prompt, raw response, screenshot, secret, or PII persistence;
- `TARGET_ENVIRONMENT_REHEARSAL_ONLY`;
- missing or invalid operator attestation;
- unsupported desktop, live computer-use, or multi-tenant claim allowed;
- governed pilot workflow not passing.
