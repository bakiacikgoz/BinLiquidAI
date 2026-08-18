# Contributing to ImperaOS

Contributions are welcome. Keep changes focused, preserve fail-closed behavior, and
do not include private data.

## Development setup

Backend development requires Python 3.11 and `uv`:

```bash
uv sync --python 3.11 --extra dev
uv run ruff check .
uv run pytest -q
uv run imperaos doctor --profile balanced --json
```

The Operator Console requires Node.js, Corepack and pnpm:

```bash
corepack enable
pnpm --dir apps/operator-panel install --frozen-lockfile
pnpm --dir apps/operator-panel lint
pnpm --dir apps/operator-panel test
pnpm --dir apps/operator-panel build
```

Install the Rust toolchain for Tauri changes.

## Pull requests

Submit a focused diff with behavior tests and documentation updates. Run the relevant
backend, UI and Tauri gates and remove secrets or private data. Security-sensitive
changes require a threat or abuse-case note, a regression test, and explicit
verification that affected paths still fail closed.

The `binliquid.*` Python package remains a supported compatibility namespace. Do not
opportunistically rename it; see
[Branding and Compatibility](docs/BRANDING_AND_COMPATIBILITY.md).

AI coding tools, including Codex, may be used in the development workflow.
Contributors remain responsible for reviewing generated changes, verifying licenses
and provenance, running tests, and ensuring submitted code satisfies project security
and quality requirements. See the
[Codex Maintainer Workflow](docs/CODEX_MAINTAINER_WORKFLOW.md).
