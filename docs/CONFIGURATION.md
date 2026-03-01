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

Planner tuning:

- `planner_tuning.repair_enabled`: bool
- `planner_tuning.repair_max_attempts`: int (`0..2`)
- `planner_tuning.prompt_variant`: `strict_v1|strict_v2|strict_v3`

Code verification tuning:

- `code_verify.enabled`: bool
- `code_verify.lint_enabled`: bool
- `code_verify.test_collect_enabled`: bool
- `code_verify.targeted_tests_enabled`: bool
- `code_verify.timeout_s`: int
- `code_verify.retry_max`: int
- `code_verify.retry_strategy`: `failure_aware|minimal_only`

sLTC calibration/tuning:

- `sltc.router_mode`: `active|shadow|off`
- `sltc.decay`
- `sltc.spike_threshold`
- `sltc.failure_penalty_weight`
- `sltc.latency_penalty_weight`
- `sltc.need_bonus`
- `sltc.conf_bonus`
- `sltc.task_bias_overrides` (`{"task:expert": value}`)

Memory salience/retrieval tuning:

- `memory.salience_decay`
- `memory.salience_threshold`
- `memory.keyword_weights`
- `memory.task_bonus`
- `memory.expert_bonus`
- `memory.spike_reduction`
- `memory.rank_salience_weight`
- `memory.rank_recency_weight`

## Common Environment Variables

Examples:

```bash
export BINLIQUID_LLM_PROVIDER=ollama
export BINLIQUID_FALLBACK_PROVIDER=transformers
export BINLIQUID_ROUTER_MODE=rule
export BINLIQUID_SHADOW_ROUTER_ENABLED=true
export BINLIQUID_FAST_PATH_REGRET_WINDOW=2
export BINLIQUID_PLANNER_REPAIR_ENABLED=true
export BINLIQUID_PLANNER_PROMPT_VARIANT=strict_v3
export BINLIQUID_CODE_VERIFY_TIMEOUT_S=20
export BINLIQUID_SLTC_ROUTER_MODE=shadow
export BINLIQUID_MEMORY_RANK_SALIENCE_WEIGHT=0.72
```

## Privacy-Safe Output

`config resolve` output redacts keys containing markers like `token/secret/password/key`.
