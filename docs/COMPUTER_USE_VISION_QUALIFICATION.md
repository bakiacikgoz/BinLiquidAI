# Computer-Use Vision Qualification

## Evidence Levels

`deterministic`
: CI-friendly mock qualification using `benchmarks/tasks/computer_use_vision/smoke_tasks.jsonl`.

`live`
: Opt-in macOS local qualification. It requires `BINLIQUID_ENABLE_REAL_VISION_COMPUTER_USE_TESTS=1`, Screen Recording, Accessibility, `macos_live_enabled=true`, and a configured local vision provider.

## Report Contract

Qualification writes a machine-readable report:

```json
{
  "artifact_version": "computer_use_vision_qualification/v1",
  "mode": "deterministic",
  "status": "pass",
  "summary": {
    "raw_screenshot_persisted_count": 0
  }
}
```

The default output path is `artifacts/computer_use_vision_qualification/qualification.json`.

Platform live evidence uses the additive `computer-use-platform-qualification/v1` schema
at `contracts/computer_use/platform_qualification.schema.json`. That report is validated
against platform, commit, config hash, backend, permission, task-suite, and safety
invariants before a platform can report `liveEnabled=true`.

## Gate Rules

- Deterministic pass permits continued development and operator preview.
- Live macOS public claims require separate local evidence.
- Windows live computer-use remains blocked until signed qualification evidence exists.
- Linux live computer-use remains blocked until platform-specific signed qualification evidence exists.
- Raw screenshot persistence must remain `0` unless an explicit local debug policy is enabled.
- Replay verification checks event integrity and policy invariants only; it does not prove task correctness.

## Commands

```bash
uv run binliquid computer-use qualify --runtime vision-first --suite smoke --mode deterministic --json
uv run binliquid computer-use vision doctor --profile balanced --json
uv run python -m binliquid computer-use doctor --profile balanced --platform all --json
uv run python scripts/evaluate_computer_use_platform_matrix.py --profile balanced --output artifacts/computer_use_platform_matrix.json --markdown artifacts/COMPUTER_USE_PLATFORM_MATRIX.md
```

Live macOS qualification is intentionally skipped unless explicitly opted in:

```bash
BINLIQUID_ENABLE_REAL_VISION_COMPUTER_USE_TESTS=1 uv run python -m pytest tests/test_computer_use_vision_acceptance.py -q
```
