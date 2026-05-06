# RFC Computer-Use 016: Vision Runtime Safety Summary

Phase 7 adds a machine-readable safety summary for every vision-first runtime
completion path. The summary is written next to the redacted audit envelope as
`vision_runtime_summary.json` and is safe to publish with replay artifacts
because it contains counters, reason codes, hashes-only audit linkage, and no
raw screenshot paths.

## Artifact Contract

The artifact version is `computer_use_vision_runtime_summary/v1`.

```json
{
  "candidate_actions_seen": 4,
  "candidate_actions_rejected": 2,
  "candidate_reject_reasons": {
    "low_confidence": 1,
    "unsupported_action": 1
  },
  "actions_executed": 1,
  "approval_blocks": 1,
  "approval_resumes": 0,
  "semantic_verification": {
    "satisfied": 1,
    "inconclusive": 0,
    "failed": 0,
    "skipped": 0
  },
  "no_progress_stops": 0,
  "raw_screenshot_persisted": 0,
  "stop_reason": "completed"
}
```

`candidate_actions_seen` counts candidate actions represented in recorded
runtime steps. `candidate_actions_rejected` and `candidate_reject_reasons`
count fail-closed policy denials recorded in those steps. `approval_resumes`
is reserved for the approval-resume path and remains `0` until that runtime
path executes a resumed snapshot.

## Operational Signals

- `raw_screenshot_persisted > 0`: SEV0 privacy regression.
- `semantic_verification.failed > 0` on reference fixtures: release blocker.
- `approval_resume_stale > 0`: expected only in drift tests; unexpected in a happy path.
- `provider_invalid_response_rate > 5%`: investigate provider prompt or model compatibility.
- `no_progress_stop_rate > 10%`: planner/provider quality issue.

Replay summaries load the safety artifact when present, so CI can compare the
same counters from the runtime output and replay view without rehydrating raw
screenshots.
