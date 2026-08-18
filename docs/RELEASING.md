# Releasing ImperaOS

Release claims require executed evidence. Do not infer readiness from implementation
or configuration alone.

## Release checklist

1. Start from a clean working tree and review the version and compatibility boundary.
2. Update `CHANGELOG.md` with verified changes only.
3. Run backend lint, tests, build, and relevant product/release closure gates.
4. Build and test the Operator Console when it is in scope.
5. Verify signing and evidence where the claimed surface requires them.
6. Review claims against the product boundary and qualification evidence.
7. Run a history-aware secret scan.
8. Prepare release notes that distinguish supported, beta, pilot, preview, gated, and
   unqualified surfaces.

Minimum backend verification:

```bash
uv sync --python 3.11 --extra dev
uv run ruff check .
uv run pytest -q
uv build
uv run imperaos --help
```

Do not publish or sign a release when required evidence is missing, stale, invalid, or
contradicts the intended claim.
