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

## Gate Rules

- Deterministic pass permits continued development and operator preview.
- Live macOS public claims require separate local evidence.
- Windows live computer-use remains blocked until signed qualification evidence exists.
- Raw screenshot persistence must remain `0` unless an explicit local debug policy is enabled.
- Replay verification checks event integrity and policy invariants only; it does not prove task correctness.

## Commands

```bash
uv run binliquid computer-use qualify --runtime vision-first --suite smoke --mode deterministic --json
uv run binliquid computer-use vision doctor --profile balanced --json
```

Live macOS qualification is intentionally skipped unless explicitly opted in:

```bash
BINLIQUID_ENABLE_REAL_VISION_COMPUTER_USE_TESTS=1 uv run python -m pytest tests/test_computer_use_vision_acceptance.py -q
```
