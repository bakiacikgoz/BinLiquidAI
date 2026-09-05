# Computer-use extension: paused

As of 2026-09-05, computer use is outside ImperaOS core product scope. Active
feature development is paused. The code is retained under `extensions/computer-use`
as the optional `imperaos-computer-use` distribution, which depends on core;
core never depends on the extension.

## Current behavior

Normal installs, Operator Panel workflows and core release checks need no desktop
drivers or platform qualification. Core capability compatibility fields remain
false with `COMPUTER_USE_EXTENSION_NOT_INSTALLED`; their `not_qualified` stage
preserves the existing contract. Historical configuration and audit records remain
readable. Installing the extension does not add a core CLI command or panel card.

## Explicit extension development

From a source checkout, run the separate commands with uv:

```bash
uv sync --extra dev
uv pip install --python .venv --no-deps -e extensions/computer-use
uv run --no-sync imperaos-computer-use --help
uv run --no-sync imperaos-computer-use doctor --json
uv run --no-sync pytest -q extensions/computer-use/tests
```

`make vision-gate` is an explicit opt-in extension check. It is excluded from
`make mainline-gate`. The root `scripts/evaluate_computer_use_*` scripts are
retained for extension work and require the optional distribution. Historical
RFCs and qualification reports document the former design; their
`imperaos computer-use` examples are superseded by the standalone CLI above.

The explicit editable installation uses the same Unicode-path-safe packaging
mode as core. Use `--no-sync` after installation; a normal core sync does not
retain this unrequested extension. The archived frontend sources are references,
not a separately runnable extension UI.

## Conditions for reconsideration

Resume development only when a concrete target-user workflow requires desktop
interaction and cannot reasonably be completed through supported API, CLI or
integration paths. Define the supported platform, workflow, owner and acceptance
evidence first. A separately maintained external execution engine is also an
option; no broad desktop-automation commitment is implied.

Any future live execution must preserve fail-closed policy, observation freshness,
approval binding, sensitive-surface denial and replay integrity. Deterministic
fixtures are regression evidence, not live-platform qualification.

## Isolation verification

The implementation was verified with 1,067 core Python tests, 209 extension tests,
37 affected frontend tests and three Chromium end-to-end scenarios passing.
Nine extension tests requiring live/explicitly enabled environments were skipped.
TypeScript, the production Vite build, Ruff and the whitespace check passed.
The core wheel excludes desktop implementation code; the optional wheel contains
the independent CLI and drivers. All 49 original Python module files were retained.

On Windows, the full core suite used a short temporary directory via `--basetemp`.
Long temporary paths also fail the pre-change enterprise qualification tests with
`WinError 206`; no qualification checks were relaxed. Live desktop automation and
native installer signing were not exercised by this change.
