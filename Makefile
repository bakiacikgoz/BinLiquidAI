.PHONY: bootstrap bootstrap-macos bootstrap-windows install lint test check doctor chat benchmark benchmark-team benchmark-ablation benchmark-energy pilot-gate enterprise-gate qualification-run vision-gate control-plane-schemas control-plane-snapshot-gate control-plane-gate evidence-pack-gate enterprise-hat-a-evidence-gate evidence-corpus-gate install-rehearsal-gate external-agent-pilot-gate governance-admin-gate agent-control-plane-v1-gate operator-panel-i18n-gate operator-panel-productization-gate operator-panel-tauri-smoke pilot-readiness-gate design-partner-rc-gate ui-gate ui-e2e-gate rust-gate mainline-gate ui-install ui-dev ui-build ui-tauri-build

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

evidence-pack-gate:
	uv run pytest -q tests/test_control_plane_evidence_pack.py
	corepack pnpm --dir apps/operator-panel test -- EvidencePackView
	corepack pnpm --dir apps/operator-panel test:e2e -- evidence.spec.ts

enterprise-hat-a-evidence-gate:
	uv run pytest -q tests/test_control_plane_qualification_closure.py tests/test_control_plane_claim_guard.py
	uv run python scripts/prepare_enterprise_fixture.py --root .
	uv run python scripts/generate_enterprise_hat_a_fixture.py --json
	uv run binliquid control-plane qualification close \
		--profile enterprise \
		--qualification-root artifacts/enterprise-hat-a/qualification \
		--output-root artifacts/enterprise-hat-a \
		--json
	uv run binliquid control-plane qualification verify \
		--profile enterprise \
		--input artifacts/enterprise-hat-a/enterprise_hat_a_closure.json \
		--json
	uv run binliquid control-plane claims verify --profile enterprise --evidence-root artifacts --json

evidence-corpus-gate:
	uv run pytest -q tests/test_control_plane_evidence_corpus.py tests/test_evidence_index.py
	uv run python scripts/prepare_enterprise_fixture.py --root .
	uv run python scripts/evaluate_evidence_corpus.py --json
	uv run binliquid control-plane evidence index \
		--profile enterprise \
		--evidence-root artifacts/evidence-corpus/valid \
		--root-dir artifacts/evidence-corpus/index-state \
		--json

install-rehearsal-gate:
	uv run pytest -q tests/test_control_plane_install_rehearsal.py
	uv run python scripts/prepare_enterprise_fixture.py --root .
	uv run binliquid control-plane install rehearsal \
		--profile enterprise \
		--target-root .binliquid/rehearsal/design-partner \
		--mode source-cli \
		--output artifacts/install-rehearsal/report.json \
		--json

external-agent-pilot-gate:
	uv run pytest -q tests/test_control_plane_external_agent_client.py tests/test_external_agent_gateway.py
	uv run python scripts/prepare_enterprise_fixture.py --root .
	uv run python scripts/run_external_agent_pilot.py --json

governance-admin-gate:
	uv run pytest -q tests/test_control_plane_admin_store.py tests/test_control_plane_policy_pack_lifecycle.py tests/test_rbac_admin.py tests/test_policy_packs.py
	uv run python scripts/prepare_enterprise_fixture.py --root .
	uv run python scripts/evaluate_governance_admin.py --json

ui-gate:
	corepack pnpm --dir apps/operator-panel qa:frontend

operator-panel-i18n-gate:
	corepack pnpm --dir apps/operator-panel i18n:coverage

operator-panel-productization-gate:
	corepack pnpm --dir apps/operator-panel qa:productization

operator-panel-tauri-smoke:
	corepack pnpm --dir apps/operator-panel tauri:smoke

pilot-readiness-gate:
	uv run ruff check .
	uv run pytest -q
	uv run python -m compileall binliquid
	uv run python -m binliquid control-plane snapshot --json
	corepack pnpm --dir apps/operator-panel test
	corepack pnpm --dir apps/operator-panel lint
	corepack pnpm --dir apps/operator-panel build
	corepack pnpm --dir apps/operator-panel test:e2e
	corepack pnpm --dir apps/operator-panel exec tsx scripts/assert-productized-pages.ts
	corepack pnpm --dir apps/operator-panel exec tsx scripts/assert-no-primary-raw-json.ts
	corepack pnpm --dir apps/operator-panel exec tsx scripts/assert-i18n-coverage.ts
	cargo test -q --manifest-path apps/operator-panel/src-tauri/Cargo.toml
	$(MAKE) agent-control-plane-v1-gate
	$(MAKE) operator-panel-tauri-smoke
	corepack pnpm --dir apps/operator-panel pilot:assert
	$(MAKE) evidence-pack-gate
	git diff --check

design-partner-rc-gate:
	uv run ruff check .
	uv run pytest -q \
		tests/test_design_partner_rc.py \
		tests/test_external_agent_gateway.py \
		tests/test_agent_registry_v2.py \
		tests/test_policy_packs.py \
		tests/test_rbac_admin.py \
		tests/test_evidence_index.py \
		tests/test_reports_alerts.py \
		tests/test_operations_runner.py \
		tests/test_control_plane_snapshot.py
	uv run python scripts/generate_control_plane_contract_schemas.py
	corepack pnpm --dir apps/operator-panel test -- controlPlaneMappers controlPlaneSnapshot
	uv run python scripts/run_external_agent_gateway_smoke.py
	uv run python scripts/evaluate_policy_pack_promotion.py
	uv run python scripts/evaluate_evidence_index.py
	uv run python scripts/evaluate_reports_alerts.py
	uv run python scripts/generate_design_partner_rc_pack.py --json
	git diff --check

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
