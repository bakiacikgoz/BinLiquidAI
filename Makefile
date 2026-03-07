.PHONY: bootstrap install lint test check doctor chat benchmark benchmark-team benchmark-ablation benchmark-energy pilot-gate enterprise-gate ui-install ui-dev ui-build ui-tauri-build

bootstrap:
	bash scripts/bootstrap_macos.sh

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
	uv run pytest -q tests/test_enterprise_cli.py
	rm -rf .binliquid/keys .binliquid/identity
	uv run python scripts/prepare_enterprise_fixture.py --root .
	uv run binliquid security baseline --profile enterprise --json
	uv run binliquid auth whoami --profile enterprise --json
	uv run binliquid auth check --profile enterprise --permission runtime.run --json
	uv run binliquid keys verify --profile enterprise --path artifacts/security_posture.json --json
	uv run binliquid metrics snapshot --profile enterprise --json
	uv run binliquid ga readiness --profile enterprise --report artifacts/ga_readiness_report.json --json
	uv run binliquid keys verify --profile enterprise --path artifacts/ga_readiness_report.json --json
	uv run binliquid support bundle export --profile enterprise --json

ui-install:
	cd apps/operator-panel && pnpm install

ui-dev:
	cd apps/operator-panel && pnpm tauri:dev

ui-build:
	cd apps/operator-panel && pnpm build

ui-tauri-build:
	cd apps/operator-panel && pnpm tauri:build
