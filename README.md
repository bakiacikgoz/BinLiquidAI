# BinLiquid AI v2.0

Offline-first, local-first hybrid assistant with product and research paths.

## Highlights

- Provider-agnostic LLM runtime (`auto -> ollama -> transformers fallback`)
- Strict planner schema + typed reason codes
- Orchestrator with timeout/retry/fallback/circuit-breaker/tool-budget controls
- Upgraded experts (`code`, `research`, `plan`) with structured payload contracts
- Persistent memory v2 (salience gate + dedup + TTL + ranked retrieval)
- Benchmark suite (`smoke`, `ablation`, `energy`)
- Research reproducibility CLI (`train-router`, `eval-router`)

## Quick Start (macOS)

```bash
make bootstrap
make install
make check
uv run binliquid doctor --profile balanced
```

Optional full HF fallback runtime:

```bash
uv sync --python 3.11 --extra dev --extra hf
```

## Chat

```bash
uv run binliquid chat --profile balanced --once "Bu haftayı 4 adıma böl"
uv run binliquid chat --profile balanced --provider auto --fallback-provider transformers
uv run binliquid chat --profile balanced --stream --fast-path
```

`chat` options:

- `--provider auto|ollama|transformers`
- `--fallback-provider transformers|ollama`
- `--session-id <id>`
- `--stream/--no-stream` (kısa mesajlarda anlık token akışı)
- `--fast-path/--no-fast-path` (kısa mesajlarda planner/router atlayıp tek çağrı)

## Benchmark

```bash
uv run binliquid benchmark smoke --mode all --profile balanced
uv run binliquid benchmark ablation --mode all --profile balanced
uv run binliquid benchmark energy --profile balanced --energy-mode measured
```

Outputs are written under `benchmarks/results/*`.

## Research

```bash
uv run binliquid research train-router \
  --dataset .binliquid/research/router_dataset.jsonl \
  --output-dir research/sltc_experiments/artifacts \
  --seed 42

uv run binliquid research eval-router \
  --dataset .binliquid/research/router_dataset.jsonl \
  --model research/sltc_experiments/artifacts/router_model.json \
  --output-dir research/sltc_experiments/artifacts
```

## Memory

```bash
uv run binliquid memory stats --profile balanced
```

## Defaults

- Web access: off
- Privacy mode: on
- Persistent memory: off in `lite`, on in `balanced/research`

## Profiles

- `lite`: minimal resources, rule router, fallback disabled
- `balanced`: production defaults, sLTC router, fallback enabled
- `research`: debug-heavy profile for reproducible experiments
