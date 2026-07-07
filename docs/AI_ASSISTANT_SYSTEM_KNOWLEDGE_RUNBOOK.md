# AI Assistant System Knowledge Runbook

## Build

```bash
uv run binliquid assistant knowledge build --profile enterprise --json
```

The build command reads allowlisted local docs, contracts, examples, route manifests, and CLI
surfaces. It writes generated artifacts under `artifacts/assistant-system-knowledge/`.

## Search

```bash
uv run binliquid assistant knowledge search --profile enterprise --query "AegisOS'ta agent'e görev ver" --json
```

Search is local-only and deterministic. If the index is missing or stale, it returns a blocked
or setup-required diagnostic instead of guessing.

## Doctor

```bash
uv run binliquid assistant knowledge doctor --profile enterprise --json
```

Doctor checks whether the manifest exists, required sources are present, and source hashes still
match the built index.

## Gate

```bash
make assistant-system-knowledge-gate
```

The gate builds the index, runs regression searches, verifies contracts, checks prompt/UI tests,
and blocks generic AegisOS answers or secret leakage.
