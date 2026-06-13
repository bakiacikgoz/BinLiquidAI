# TurboVec Experimental Backend

TurboVec support is a guarded optional adapter. It is not a default runtime dependency and does not affect release claims.

Required posture:

- `turbovec_experimental_enabled=false` by default.
- Missing package or disabled flag must produce a non-failing `disabled` or `unavailable` status.
- Dimension and bit-depth guards are read from config before backend activation.
- Artifacts must describe TurboVec as experimental only.

Validation:

```bash
uv run python scripts/run_memory_index_gate.py
```

The gate expects TurboVec to stay disabled unless an operator intentionally enables the experimental path.
