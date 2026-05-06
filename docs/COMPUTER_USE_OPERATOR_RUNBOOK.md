# Computer-Use Operator Runbook

## Daily Status Check

```bash
uv run binliquid computer-use doctor --platform all --json
uv run binliquid operator capabilities --json
```

Expected default:

```text
macOS: not_configured or not_qualified, liveEnabled=false
Windows: not_qualified, liveEnabled=false
Linux: not_qualified, liveEnabled=false
```

## macOS Qualification

1. Close unrelated sensitive windows.
2. Confirm Screen Recording and Accessibility are manually granted.
3. Configure a local strict-JSON provider.
4. Run the macOS doctor.
5. Run opt-in live qualification only under supervision.
6. Verify the report with:

```bash
uv run binliquid computer-use qualification verify \
  --platform macos \
  --report artifacts/computer_use/macos_qualification_report.json \
  --json
```

Replay/audit verification for the macOS qualification report is separate:

```bash
uv run binliquid computer-use replay \
  --report artifacts/computer_use/macos_qualification_report.json \
  --verify \
  --json
```

The live fixture command requires all of:

```text
BINLIQUID_COMPUTER_USE_LIVE_MACOS=1
BINLIQUID_COMPUTER_USE_SUPERVISED_FIXTURE_ONLY=1
BINLIQUID_COMPUTER_USE_REQUIRE_STEP_APPROVAL=1
BINLIQUID_COMPUTER_USE_ACK=I understand BinLiquid will control my macOS desktop only for local supervised fixtures.
```

Without those values and a ready local provider, permissions, backends, matching
commit/config hash, and safety defaults, macOS remains blocked and
`liveEnabled=false`. Blocked preflight reports can still replay-verify
successfully for audit integrity; qualification pass/fail is reported
separately as `qualificationPassed`.

Provider readiness is checked with a synthetic non-sensitive fixture image:

```bash
uv run binliquid computer-use provider doctor \
  --provider ollama \
  --model <local-vision-model> \
  --synthetic-fixture \
  --json
```

Do not run `ollama pull` automatically from the agent. The operator may run `ollama --version`, `ollama list`, `ollama serve`, and model pulls manually. A passing macOS fixture report means `fixtureQualified=true`, `productionQualified=false`, and `liveEnabled=false` by default; Windows and Linux remain unqualified.
Provider doctor reports deterministic blockers such as `VISION_PROVIDER_MODEL_NOT_CONFIGURED`, `VISION_PROVIDER_MODEL_NOT_FOUND`, `VISION_PROVIDER_NOT_VISION_CAPABLE`, `VISION_PROVIDER_INVALID_RESPONSE`, `VISION_PROVIDER_TIMEOUT`, and `VISION_PROVIDER_UNAVAILABLE`.

Strict provider responses may include `candidate_actions`. The planner treats a
missing or empty `candidate_actions` list as a safe stop, rejects invalid action
types, low-confidence actions, and invalid target boxes before policy
classification, and still routes click/type/hotkey-style actions through step
approval before execution.
The frozen provider response schema is
`contracts/computer_use/vision_provider_response.schema.json`.

The vision-first loop stops before input execution if the same normalized action
digest is selected again or if consecutive `wait` actions exceed
`max_consecutive_wait_actions`. The stop reasons are
`VISION_REPEATED_ACTION_REJECTED` and `VISION_WAIT_BUDGET_EXCEEDED`.

Preflight writes Phase 4E readiness artifacts:

```text
artifacts/computer_use/macos_phase4e_preflight.json
artifacts/computer_use/macos_phase4e_flag_inventory.json
artifacts/computer_use/macos_phase4e_permission_readiness.json
```

## Stop Conditions

Stop the run if a sensitive surface appears, an approval is stale, terminal control is requested, a no-progress loop is detected, or raw screenshot persistence would be required by default.
