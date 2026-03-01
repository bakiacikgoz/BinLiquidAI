# BENCHMARK_PROTOCOL

## Smoke Benchmark (Ablation)

- A modu: LLM-only baseline
- B modu: Rule-router enabled
- C modu: sLTC router enabled
- D modu: sLTC router + memory salience
- Task set: `benchmarks/tasks/smoke_tasks.jsonl`

## Metrikler

- `success_rate`
- `p50_latency_ms`
- `p95_latency_ms`
- `peak_ram_mb`
- `fallback_rate`
- `wrong_route_rate`
- `expert_call_rate`
- `memory_write_rate`
- `energy_estimate_wh` (yaklaşık sistem seviyesi)

## Çalıştırma

```bash
uv run binliquid benchmark smoke --mode all --profile balanced
```

Hızlı smoke doğrulaması için `--task-limit` kullanılabilir:

```bash
uv run binliquid benchmark smoke --mode all --profile balanced --task-limit 2
```

Çıktı dosyası varsayılan olarak `benchmarks/results/smoke_<timestamp>.json` altına yazılır.
