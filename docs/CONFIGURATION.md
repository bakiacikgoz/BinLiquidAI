# CONFIGURATION (v0.2)

## Sources and Precedence

Resolved runtime config uses this strict order:

1. defaults (model)
2. profile TOML (`config/<profile>.toml`)
3. env vars (`BINLIQUID_*`)
4. CLI overrides

Command:

```bash
uv run binliquid config resolve --profile balanced --json
```

## Important Fields

- `llm_provider`: `auto|ollama|transformers`
- `fallback_provider`: `transformers|ollama`
- `fallback_enabled`: bool
- `router_mode`: `rule|sltc`
- `shadow_router_enabled`: bool
- `shadow_router_mode`: `rule|sltc`
- `fast_path_regret_window`: int (turn window)
- `fast_path_regret_threshold`: float
- `memory_ttl_days`: int

## Common Environment Variables

Examples:

```bash
export BINLIQUID_LLM_PROVIDER=ollama
export BINLIQUID_FALLBACK_PROVIDER=transformers
export BINLIQUID_ROUTER_MODE=rule
export BINLIQUID_SHADOW_ROUTER_ENABLED=true
export BINLIQUID_FAST_PATH_REGRET_WINDOW=2
```

## Privacy-Safe Output

`config resolve` output redacts keys containing markers like `token/secret/password/key`.
