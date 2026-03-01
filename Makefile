.PHONY: bootstrap install lint test check doctor chat benchmark

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
	uv run binliquid doctor

chat:
	uv run binliquid chat --profile lite

benchmark:
	uv run binliquid benchmark smoke --mode all --profile balanced
