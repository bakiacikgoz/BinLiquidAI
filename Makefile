.PHONY: bootstrap bootstrap-macos bootstrap-windows install lint test check doctor chat benchmark benchmark-team benchmark-ablation benchmark-energy pilot-gate enterprise-gate qualification-run vision-gate control-plane-schemas control-plane-snapshot-gate control-plane-gate agent-control-plane-v1-gate operator-panel-productization-gate ui-gate ui-e2e-gate rust-gate mainline-gate ui-install ui-dev ui-build ui-tauri-build

bootstrap: bootstrap-macos

bootstrap-macos:
	bash scripts/bootstrap_macos.sh

bootstrap-windows:
	powershell -NoProfile -ExecutionPolicy Bypass -File scripts/bootstrap_windows.ps1

install:
	uv sync --python 3.11 --extra dev

lint:
	uv run ruff check .

test:
	uv run pytest -q

check: lint test

doctor:
	uv run binliquid doctor --profile balanced

chat:
	uv run binliquid chat --profile lite

benchmark:
	uv run binliquid benchmark smoke --mode all --profile balanced

benchmark-team:
	uv run binliquid benchmark team --profile balanced --suite smoke --spec team.yaml

benchmark-ablation:
	uv run binliquid benchmark ablation --mode all --profile balanced

benchmark-energy:
	uv run binliquid benchmark energy --profile balanced --energy-mode measured

pilot-gate:
	uv run pytest -q \
		tests/test_team_bounded_concurrency.py \
		tests/test_team_governance.py \
		tests/test_team_memory_fail_closed.py \
		tests/test_team_audit_envelope.py \
		tests/test_team_cli.py \
		tests/test_team_pilot_gate.py
	uv run binliquid team validate --spec examples/team/restricted_pilot.yaml --json
	uv run binliquid team pilot-check \
		--spec examples/team/restricted_pilot.yaml \
		--profile restricted \
		--mode deterministic \
		--report artifacts/team_pilot_report.json \
		--json

enterprise-gate:
	uv run pytest -q tests/test_enterprise_cli.py tests/test_enterprise_qualification.py
	rm -rf .binliquid/keys .binliquid/identity
	rm -f artifacts/qualification_report.json artifacts/QUALIFICATION_REPORT.md
	uv run python scripts/prepare_enterprise_fixture.py --root .
	uv run binliquid security baseline --profile enterprise --json
	uv run binliquid auth whoami --profile enterprise --json
	uv run binliquid auth check --profile enterprise --permission runtime.run --json
	uv run binliquid keys verify --profile enterprise --path artifacts/security_posture.json --json
	uv run binliquid metrics snapshot --profile enterprise --json
	uv run binliquid ga readiness --profile enterprise --report artifacts/ga_readiness_report.json --json
	uv run binliquid keys verify --profile enterprise --path artifacts/ga_readiness_report.json --json
	uv run binliquid support bundle export --profile enterprise --json

vision-gate:
	uv run --extra dev pytest -q \
		tests/test_computer_use_vision_contracts.py \
		tests/test_computer_use_vision_provider.py \
		tests/test_computer_use_vision_planner.py \
		tests/test_computer_use_vision_policy.py \
		tests/test_computer_use_vision_approval.py \
		tests/test_computer_use_vision_verifier.py \
		tests/test_computer_use_vision_runtime.py \
		tests/test_computer_use_vision_qualification.py \
		tests/test_computer_use_vision_replay.py \
		tests/test_computer_use_macos_supervised_v2_gate.py
	uv run python -m binliquid computer-use doctor --json
	uv run python scripts/evaluate_computer_use_platform_matrix.py \
		--profile balanced \
		--output artifacts/computer_use/platform_matrix.json \
		--markdown artifacts/computer_use/PLATFORM_MATRIX.md
	uv run python scripts/evaluate_macos_supervised_vision_gate.py \
		--evidence-root artifacts/computer_use \
		--output artifacts/computer_use/macos_supervised_v2_gate.json \
		--markdown artifacts/computer_use/MACOS_SUPERVISED_V2_GATE.md \
		--json

control-plane-schemas:
	uv run python scripts/generate_control_plane_contract_schemas.py

control-plane-snapshot-gate:
	uv run binliquid control-plane snapshot --json
	uv run pytest -q tests/test_control_plane_snapshot.py
	corepack pnpm --dir apps/operator-panel test -- controlPlaneSnapshot

control-plane-gate:
	uv run pytest -q \
		tests/test_control_plane_models.py \
		tests/test_control_plane_registry.py \
		tests/test_control_plane_policy_simulator.py \
		tests/test_control_plane_evidence_pack.py \
		tests/test_control_plane_claim_guard.py \
		tests/test_control_plane_cli.py \
		tests/test_control_plane_snapshot.py
	uv run python scripts/generate_control_plane_contract_schemas.py
	git diff --exit-code contracts/control_plane
	uv run binliquid control-plane doctor --profile enterprise --json
	uv run binliquid control-plane snapshot --profile enterprise --json
	uv run python scripts/evaluate_control_plane_claims.py --profile enterprise --json

ui-gate:
	corepack pnpm --dir apps/operator-panel qa:frontend

operator-panel-productization-gate:
	corepack pnpm --dir apps/operator-panel qa:productization

ui-e2e-gate:
	corepack pnpm --dir apps/operator-panel test:e2e

rust-gate:
	cargo test -q --manifest-path apps/operator-panel/src-tauri/Cargo.toml

mainline-gate:
	uv run --extra dev ruff check .
	uv run --extra dev pytest -q
	$(MAKE) control-plane-gate
	$(MAKE) vision-gate
	$(MAKE) ui-gate
	$(MAKE) rust-gate
	git diff --check

agent-control-plane-v1-gate:
	$(MAKE) control-plane-gate
	$(MAKE) enterprise-gate
	$(MAKE) pilot-gate
	$(MAKE) ui-gate
	$(MAKE) rust-gate
	uv run python scripts/build_control_plane_release_pack.py --profile enterprise --output artifacts/release-pack/control-plane-v1 --json

qualification-run:
	uv run binliquid qualification run \
		--profile enterprise \
		--mode mixed \
		--soak-hours 6 \
		--output-root artifacts/qualification \
		--json

ui-install:
	cd apps/operator-panel && pnpm install

ui-dev:
	cd apps/operator-panel && pnpm tauri:dev

ui-build:
	cd apps/operator-panel && pnpm build

ui-tauri-build:
	cd apps/operator-panel && pnpm tauri:build
