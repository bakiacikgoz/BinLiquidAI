# RELEASE_CHECKLIST

## Quality Gates

- [ ] `uv run ruff check .`
- [ ] `uv run pytest -q`
- [ ] `make pilot-gate`
- [ ] `make enterprise-gate`
- [ ] `make qualification-run`
- [ ] `uv run binliquid team validate --spec examples/team/restricted_pilot.yaml --json`
- [ ] `uv run binliquid team pilot-check --spec examples/team/restricted_pilot.yaml --profile restricted --mode deterministic --report artifacts/team_pilot_report.json --json`
- [ ] `artifacts/team_pilot_report.json` shows `checks.bounded_concurrency.status=pass`
- [ ] `uv run binliquid config resolve --profile balanced --json`
- [ ] `uv run binliquid doctor --profile balanced`
- [ ] `uv run binliquid benchmark smoke --mode all --profile balanced`
- [ ] `uv run binliquid benchmark team --profile restricted --suite smoke --spec team.yaml --deterministic-mock`
- [ ] `uv run binliquid benchmark team --profile balanced --suite smoke --spec team.yaml`
- [ ] `uv run binliquid benchmark ablation --mode all --profile balanced --suite quality`
- [ ] `uv run binliquid benchmark energy --profile balanced --energy-mode measured`
- [ ] `uv run pytest -q tests/test_memory_concurrency.py`
- [ ] `uv run pytest -q tests/test_team_checkpoint_concurrency.py`

## Enterprise Gates

- [ ] `uv run python scripts/prepare_enterprise_fixture.py --root .`
- [ ] `uv run binliquid security baseline --profile enterprise --json`
- [ ] `uv run binliquid auth whoami --profile enterprise --json`
- [ ] `uv run binliquid auth check --profile enterprise --permission runtime.run --json`
- [ ] `uv run binliquid metrics snapshot --profile enterprise --json`
- [ ] `uv run binliquid qualification run --profile enterprise --mode mixed --soak-hours 6 --output-root artifacts/qualification --json`
- [ ] `uv run binliquid ga readiness --profile enterprise --report artifacts/ga_readiness_report.json --json`
- [ ] `artifacts/security_posture.json` exists and is signed
- [ ] `artifacts/metrics_snapshot.json` exists and is signed
- [ ] `artifacts/qualification_report.json` exists, is signed, and contains all required workloads
- [ ] `artifacts/QUALIFICATION_REPORT.md` exists
- [ ] `artifacts/ga_readiness_report.json` exists and is signed
- [ ] `artifacts/GA_READINESS_REPORT.md` exists
- [ ] key status reports asymmetric provider and trusted verification keys
- [ ] qualification evidence is published before any `enterprise deployment-ready` claim

## Research Gates

- [ ] `uv run binliquid research train-router --dataset .binliquid/research/router_dataset.jsonl`
- [ ] `uv run binliquid research eval-router --dataset .binliquid/research/router_dataset.jsonl`

## Operator Panel Gates (v0.5)

- [ ] `pnpm install --dir apps/operator-panel`
- [ ] `pnpm --dir apps/operator-panel lint`
- [ ] `pnpm --dir apps/operator-panel test`
- [ ] `pnpm --dir apps/operator-panel build`
- [ ] `cargo test -q --manifest-path apps/operator-panel/src-tauri/Cargo.toml`
- [ ] `uv run binliquid operator capabilities --json`
- [ ] `uv run binliquid team list --root-dir .binliquid/team/jobs --json`
- [ ] `uv run binliquid approval show --id <approval_id> --json`

## macOS Signing + Notarization (v0.5)

- [ ] GitHub Environment `release-macos` exists and required reviewers/policies are configured
- [ ] Signing cert secrets set:
  - `MACOS_SIGNING_IDENTITY`
  - `MACOS_SIGNING_CERT_P12_B64`
  - `MACOS_SIGNING_CERT_PASSWORD`
- [ ] Notarization auth set (choose one, API key preferred):
  - API key: `APPLE_NOTARY_KEY_ID`, `APPLE_NOTARY_ISSUER_ID`, `APPLE_NOTARY_KEY_P8_B64`
  - Apple ID: `APPLE_ID`, `APPLE_TEAM_ID`, `APPLE_APP_PASSWORD`
- [ ] `apps/operator-panel/scripts/codesign_notarize_macos.sh <App.app> <artifact.dmg>`
- [ ] `codesign --verify --deep --strict` PASS
- [ ] `xcrun notarytool submit --wait` PASS
- [ ] `xcrun stapler staple` + `xcrun stapler validate` PASS
- [ ] Clean-machine quarantine/Gatekeeper open test PASS

## Artifact Checks

- [ ] `artifacts/status.json` exists and valid JSON
- [ ] `artifacts/test_summary.json` exists and valid JSON
- [ ] `artifacts/benchmark_summary.json` exists and valid JSON
- [ ] `artifacts/router_shadow_summary.json` exists and valid JSON
- [ ] `artifacts/research_summary.json` exists and valid JSON
- [ ] `artifacts/team_summary.json` exists and valid JSON
- [ ] `artifacts/team_pilot_report.json` exists and reports `overall_status=pass`
- [ ] `artifacts/security_posture.json` exists and reports `overall_status=pass`
- [ ] `artifacts/metrics_snapshot.json` exists and valid JSON
- [ ] `artifacts/qualification_report.json` exists and reports a support boundary table
- [ ] `artifacts/ga_readiness_report.json` exists and reports no `red` blocker before GA review
- [ ] Benchmark JSON outputs exist under `benchmarks/results/`
- [ ] Ablation Markdown report exists
- [ ] Team run artifacts exist under `.binliquid/team/jobs/<job_id>/`
- [ ] `uv run binliquid team replay --job-id <id> --root-dir .binliquid/team/jobs --verify --json` passes on clean smoke traces
- [ ] `uv run binliquid team resume --spec team.yaml --job-id <id> --root-dir .binliquid/team/jobs --json` only works when approvals are `executed` and not yet `consumed`
- [ ] README command examples are current
- [ ] Pre-production: one real provider team E2E run completed in target environment

## Controlled Pilot Smoke

- [ ] `uv run binliquid team pilot-check --spec examples/team/restricted_pilot_live.yaml --profile restricted --mode live-provider --provider auto --report artifacts/team_pilot_live_report.json --json`
- [ ] live-provider report classifies failures (`failure_class`) and reports `bounded_concurrency_status=pass`
- [ ] live smoke emits audit envelope, replay verify passes, and tamper probe still fails under the same release candidate
- [ ] approval reuse probe remains blocked after the live smoke
