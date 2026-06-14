# Memory Retrieval Evaluation Runbook

Run the retrieval quality suite with:

```bash
make memory-retrieval-quality-gate
```

The report is written to `artifacts/memory-semantic/retrieval_quality_report.json`.

Pass criteria:

- Top-k recall is at least 0.8.
- `hardNegativeLeakCount` is `0`.
- `scopeViolationCount` is `0`.
- `rawLeakCount` is `0`.
- `staleResultCount` and `expiredResultCount` are `0`.

Evaluation cases are JSONL records with query text, workspace/principal ids, requested scopes, expected memory ids, and hard-negative memory ids. Evidence stores the query hash only.
