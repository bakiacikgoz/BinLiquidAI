.PHONY: bootstrap bootstrap-macos bootstrap-windows install lint test check doctor chat benchmark benchmark-team benchmark-ablation benchmark-energy pilot-gate enterprise-gate qualification-run vision-gate provider-native-gate provider-runtime-gate provider-workflow-proof-gate provider-governance-pr-readiness target-evidence-rehearsal-gate operator-attestation-gate design-partner-pilot-candidate-gate design-partner-rc-audit-gate memory-governance-gate memory-index-gate memory-authority-gate memory-operator-panel-gate memory-runtime-gate memory-context-pack-gate memory-sync-gate governed-memory-v1-gate workspace-memory-authority-gate memory-rbac-gate memory-workspace-sync-gate memory-migration-dry-run-gate memory-authority-operator-gate semantic-memory-index-gate memory-retrieval-quality-gate memory-privacy-leakage-gate memory-backend-benchmark-gate control-plane-schemas control-plane-snapshot-gate control-plane-gate evidence-pack-gate enterprise-hat-a-evidence-gate evidence-corpus-gate install-rehearsal-gate external-agent-pilot-gate external-agent-v1-1-gate pilot-operations-gate governance-admin-gate security-review-pack-gate operator-panel-fallow-report operator-panel-boundary-gate operator-panel-fallow-gate ci-node24-inventory design-partner-beta-pack design-partner-beta-gate design-partner-pilot-gate agent-control-plane-v1-gate operator-panel-i18n-gate operator-panel-productization-gate operator-panel-tauri-smoke pilot-readiness-gate design-partner-rc-gate ui-gate ui-e2e-gate rust-gate mainline-gate ui-install ui-dev ui-build ui-tauri-build

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

provider-native-gate:
	uv run python scripts/run_provider_native_adapter_gate.py --profile enterprise --json

provider-runtime-gate:
	uv run pytest -q tests/test_provider_runtime_evidence.py tests/test_provider_invocation_coordinator.py
	uv run binliquid provider invoke \
		--provider openai_responses \
		--model gpt-placeholder \
		--profile enterprise \
		--mode dry-run \
		--once "Inspect service alerts and draft read-only triage summary" \
		--json

provider-workflow-proof-gate:
	uv run pytest -q tests/test_provider_runtime_workflow_proof.py
	uv run python scripts/run_provider_runtime_workflow_proof.py \
		--profile enterprise \
		--provider openai_responses \
		--mode dry-run \
		--output-root artifacts/provider-runtime/workflow-proof \
		--json

design-partner-rc-audit-gate:
	uv run python scripts/run_design_partner_rc_audit_gate.py \
		--profile enterprise \
		--allow-expected-conditionals \
		--output artifacts/design-partner-rc/rc_audit_gate.json \
		--json

memory-governance-gate:
	uv run python scripts/run_memory_governance_gate.py

memory-index-gate:
	uv run python scripts/run_memory_index_gate.py

memory-authority-gate:
	uv run python scripts/run_memory_authority_gate.py

memory-operator-panel-gate:
	uv run python scripts/run_memory_operator_panel_gate.py

memory-runtime-gate:
	uv run pytest -q tests/test_memory_runtime_bridge.py tests/test_orchestrator_memory_runtime.py tests/test_team_memory_runtime_bridge.py tests/test_control_plane_snapshot_memory_runtime.py
	uv run python scripts/run_memory_runtime_gate.py

memory-context-pack-gate:
	uv run pytest -q tests/test_memory_context_pack.py
	uv run python scripts/run_memory_context_pack_gate.py

memory-sync-gate:
	uv run pytest -q tests/test_memory_sync_pack.py tests/test_memory_sync_importer.py tests/test_memory_sync_cli.py
	uv run python scripts/run_memory_sync_gate.py

workspace-memory-authority-gate:
	uv run pytest -q \
		tests/test_memory_workspace_authority.py \
		tests/test_memory_access_evaluator.py \
		tests/test_memory_workspace_sync.py \
		tests/test_memory_migration_planner.py \
		tests/test_memory_authority_cli.py \
		tests/test_memory_runtime_workspace_integration.py \
		tests/test_memory_authority_snapshot.py \
		tests/test_memory_authority_no_raw_leakage.py
	uv run python scripts/generate_memory_workspace_contract_schemas.py
	uv run python scripts/run_workspace_memory_authority_gate.py
	$(MAKE) memory-rbac-gate
	$(MAKE) memory-workspace-sync-gate
	$(MAKE) memory-migration-dry-run-gate
	$(MAKE) memory-authority-operator-gate

memory-rbac-gate:
	uv run pytest -q tests/test_memory_access_evaluator.py
	uv run python scripts/run_memory_rbac_gate.py

memory-workspace-sync-gate:
	uv run pytest -q tests/test_memory_workspace_sync.py
	uv run python scripts/run_memory_workspace_sync_gate.py

memory-migration-dry-run-gate:
	uv run pytest -q tests/test_memory_migration_planner.py
	uv run python scripts/run_memory_migration_dry_run_gate.py

memory-authority-operator-gate:
	uv run pytest -q tests/test_memory_authority_snapshot.py
	uv run python scripts/run_memory_authority_operator_gate.py
	pnpm --dir apps/operator-panel install --frozen-lockfile
	pnpm --dir apps/operator-panel exec vitest run src/memory-authority/MemoryAuthorityView.test.tsx src/routeRegistry.test.ts

semantic-memory-index-gate:
	uv run pytest -q \
		tests/test_memory_semantic_models.py \
		tests/test_memory_embedding_provider.py \
		tests/test_memory_semantic_index_manifest.py \
		tests/test_memory_semantic_index_router.py \
		tests/test_memory_hybrid_retriever.py \
		tests/test_memory_turbovec_backend_optional.py \
		tests/test_memory_semantic_cli.py \
		tests/test_control_plane_memory_semantic_snapshot.py
	uv run python scripts/generate_memory_semantic_contract_schemas.py
	uv run python scripts/run_semantic_memory_index_gate.py
	pnpm --dir apps/operator-panel install --frozen-lockfile
	pnpm --dir apps/operator-panel exec vitest run src/memory-semantic/MemorySemanticIndexView.test.tsx src/routeRegistry.test.ts

memory-retrieval-quality-gate:
	uv run pytest -q tests/test_memory_retrieval_quality.py
	uv run python scripts/run_memory_retrieval_quality_gate.py

memory-privacy-leakage-gate:
	uv run pytest -q tests/test_memory_privacy_leakage.py
	uv run python scripts/run_memory_privacy_leakage_gate.py

memory-backend-benchmark-gate:
	uv run python scripts/run_memory_backend_benchmark.py

governed-memory-v1-gate:
	uv run pytest -q tests/test_memory_v3_governance.py tests/test_memory_cli_v3.py tests/test_control_plane_snapshot_memory_v3.py
	uv run python scripts/generate_memory_contract_schemas.py
	$(MAKE) memory-governance-gate
	$(MAKE) memory-index-gate
	$(MAKE) memory-authority-gate
	$(MAKE) memory-operator-panel-gate

provider-governance-pr-readiness:
	uv run python scripts/check_provider_governance_pr_readiness.py \
		--profile enterprise \
		--branch $$(git branch --show-current) \
		--output artifacts/provider-governance-pr/readiness.json \
		--json

target-evidence-rehearsal-gate:
	uv run --extra dev pytest -q tests/test_target_evidence_session.py tests/test_target_evidence_rehearsal.py
	uv run python scripts/prepare_target_evidence_session.py \
		--profile enterprise \
		--mode rehearsal \
		--environment-label local-enterprise-rehearsal \
		--output-root artifacts/design-partner-target-evidence \
		--json
	uv run python scripts/collect_target_evidence_rehearsal.py \
		--session artifacts/design-partner-target-evidence/session.json \
		--output-root artifacts/design-partner-target-evidence \
		--json
	uv run python scripts/verify_target_evidence_bundle.py \
		--bundle artifacts/design-partner-target-evidence/target_evidence_bundle.json \
		--json

operator-attestation-gate:
	uv run --extra dev pytest -q tests/test_operator_attestation.py
	uv run python scripts/prepare_target_evidence_session.py \
		--profile enterprise \
		--mode rehearsal \
		--environment-label local-enterprise-rehearsal \
		--output-root artifacts/design-partner-target-evidence \
		--json
	uv run python scripts/generate_operator_attestation.py \
		--session artifacts/design-partner-target-evidence/session.json \
		--operator-display-name local-operator \
		--output-root artifacts/design-partner-target-evidence \
		--json

design-partner-pilot-candidate-gate:
	uv run --extra dev pytest -q tests/test_pilot_candidate_pack.py tests/test_pr_readiness_gate.py
	$(MAKE) target-evidence-rehearsal-gate
	$(MAKE) operator-attestation-gate
	uv run python scripts/generate_design_partner_rc_pack.py \
		--profile enterprise \
		--output artifacts/design-partner-rc \
		--target-evidence-root artifacts/design-partner-target-evidence \
		--json
	uv run python scripts/generate_design_partner_pilot_candidate_pack.py \
		--profile enterprise \
		--target-evidence-root artifacts/design-partner-target-evidence \
		--rc-root artifacts/design-partner-rc \
		--output-root artifacts/design-partner-pilot-candidate \
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

external-agent-v1-1-gate:
	uv run pytest -q tests/test_external_agent_gateway.py tests/test_external_agent_gateway_v1_1.py
	uv run python scripts/generate_control_plane_contract_schemas.py
	test -f contracts/control_plane/external_agent_request_v1_1.schema.json
	test -f contracts/control_plane/external_agent_result_v1_1.schema.json
	uv run python scripts/run_external_agent_v1_1_pilot.py --json

pilot-operations-gate:
	uv run pytest -q tests/test_pilot_operations.py tests/test_control_plane_snapshot.py
	uv run binliquid pilot first-run --json
	uv run binliquid control-plane snapshot --profile enterprise --json
	corepack pnpm --dir apps/operator-panel test -- controlPlaneSnapshot

governance-admin-gate:
	uv run pytest -q tests/test_control_plane_admin_store.py tests/test_control_plane_policy_pack_lifecycle.py tests/test_rbac_admin.py tests/test_policy_packs.py
	uv run python scripts/prepare_enterprise_fixture.py --root .
	uv run python scripts/evaluate_governance_admin.py --json

security-review-pack-gate:
	uv run pytest -q tests/test_control_plane_security_review.py
	uv run python scripts/prepare_enterprise_fixture.py --root .
	uv run binliquid control-plane security review \
		--profile enterprise \
		--output-root artifacts/security-review \
		--evidence-root artifacts/evidence-corpus/valid \
		--json

operator-panel-fallow-report:
	FALLOW_TELEMETRY_DISABLED=1 DO_NOT_TRACK=1 corepack pnpm --dir apps/operator-panel fallow:report

operator-panel-boundary-gate: operator-panel-fallow-report
	BOUNDARY_GATE_MODE=enforce corepack pnpm --dir apps/operator-panel fallow:boundary

operator-panel-fallow-gate: operator-panel-fallow-report
	BOUNDARY_GATE_MODE=enforce corepack pnpm --dir apps/operator-panel fallow:boundary
	FALLOW_GATE_MODE=$${FALLOW_GATE_MODE:-warn} corepack pnpm --dir apps/operator-panel fallow:policy
	corepack pnpm --dir apps/operator-panel test -- scripts/fallow-policy

ci-node24-inventory:
	uv run pytest -q tests/test_ci_node_action_inventory.py
	uv run python scripts/collect_ci_node_action_inventory.py --workflow-root .github/workflows --output-root artifacts/ci --json

design-partner-beta-pack:
	uv run pytest -q tests/test_design_partner_beta_pack.py
	uv run python scripts/generate_design_partner_beta_pack.py --json

design-partner-beta-gate:
	$(MAKE) design-partner-pilot-gate
	$(MAKE) operator-panel-fallow-gate
	$(MAKE) ci-node24-inventory
	$(MAKE) external-agent-v1-1-gate
	$(MAKE) pilot-operations-gate
	$(MAKE) design-partner-beta-pack
	uv run ruff check .
	uv run pytest -q
	corepack pnpm --dir apps/operator-panel test
	corepack pnpm --dir apps/operator-panel lint
	corepack pnpm --dir apps/operator-panel build
	corepack pnpm --dir apps/operator-panel test:e2e
	cargo test -q --manifest-path apps/operator-panel/src-tauri/Cargo.toml
	git diff --check

design-partner-pilot-gate:
	uv run ruff check .
	uv run pytest -q
	corepack pnpm --dir apps/operator-panel test
	corepack pnpm --dir apps/operator-panel lint
	corepack pnpm --dir apps/operator-panel build
	corepack pnpm --dir apps/operator-panel pilot-launch:assert
	corepack pnpm --dir apps/operator-panel test:e2e
	cargo test -q --manifest-path apps/operator-panel/src-tauri/Cargo.toml
	$(MAKE) enterprise-hat-a-evidence-gate
	$(MAKE) evidence-corpus-gate
	$(MAKE) install-rehearsal-gate
	$(MAKE) external-agent-pilot-gate
	$(MAKE) governance-admin-gate
	$(MAKE) security-review-pack-gate
	uv run python scripts/generate_design_partner_pilot_pack.py --output-root artifacts/design-partner-pilot --json
	git diff --check

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
		tests/test_design_partner_rc_pack.py \
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
	$(MAKE) enterprise-hat-a-evidence-gate
	uv run python scripts/run_external_agent_gateway_smoke.py
	uv run python scripts/evaluate_policy_pack_promotion.py
	uv run python scripts/evaluate_evidence_index.py --profile enterprise --evidence-root artifacts/control-plane/evidence --select-latest-valid --staged-evidence-root artifacts/design-partner-rc/evidence-sample --root-dir artifacts/design-partner-rc/evidence-index/state --output artifacts/design-partner-rc/evidence_index.json
	uv run python scripts/evaluate_reports_alerts.py --profile enterprise --root-dir .binliquid/control-plane --evidence-root artifacts --output-dir artifacts/design-partner-rc/reports-alerts-logs
	uv run python scripts/generate_design_partner_rc_pack.py --profile enterprise --state-root .binliquid/control-plane --evidence-root artifacts --output artifacts/design-partner-rc --fail-on-conditional --json
	git diff --check

ui-e2e-gate:
	corepack pnpm --dir apps/operator-panel test:e2e

rust-gate:
	cargo test -q --manifest-path apps/operator-panel/src-tauri/Cargo.toml

mainline-gate:
	uv run --extra dev ruff check .
	uv run --extra dev pytest -q
	$(MAKE) provider-native-gate
	$(MAKE) provider-runtime-gate
	$(MAKE) provider-workflow-proof-gate
	$(MAKE) design-partner-pilot-candidate-gate
	$(MAKE) design-partner-rc-audit-gate
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
