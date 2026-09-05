# Computer-use extension — development paused

This optional research module is outside the ImperaOS core product and release
criteria. Active feature development is paused until a concrete user workflow
requires desktop interaction. Existing drivers, qualification gates, approval
checks and replay code are retained; no supported live platform is promised.

The dependency runs from this extension to ImperaOS. Installing core does not
install this package, load its drivers or register its commands. The main
Operator Panel does not expose desktop automation. Historical core capability
fields remain disabled for wire compatibility, including when this package is
installed; use the extension's doctor to inspect the extension itself.

## Explicit developer installation

From the repository root, with Python 3.11:

```sh
uv sync --extra dev
uv pip install --python .venv --no-deps -e extensions/computer-use
uv run --no-sync imperaos-computer-use --help
uv run --no-sync imperaos-computer-use doctor --profile balanced --platform all --json
uv run --no-sync pytest extensions/computer-use/tests
```

Use `--no-sync` for subsequent commands: a normal core `uv sync` intentionally
does not retain an unrequested optional package. The old
`imperaos computer-use ...` command is replaced by `imperaos-computer-use ...`.
Python integrations must import `imperaos_computer_use` instead of
`imperaos.computer_use`.

Normal profiles set `computer_use.enabled = false`. Installation alone does not
enable execution. Any explicit extension configuration must still satisfy the
existing provider, permissions, policy, approval and platform qualification gates.
Do not weaken those gates to revive an old workflow.

The retained frontend sources, where present, are archival references rather than
an integrated optional UI. Reintroducing a UI or resuming active development
requires a concrete workflow, an owner and fresh platform qualification evidence.
