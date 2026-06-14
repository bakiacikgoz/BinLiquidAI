# TurboVec Experimental Backend

TurboVec is represented as an optional experimental backend. It is disabled by default, cannot be used for runtime injection by default, and does not add a required dependency.

If the `turbovec` Python package is missing, backend doctor reports:

```json
{
  "status": "unavailable_optional",
  "reasonCodes": ["MEMORY_TURBOVEC_OPTIONAL_DEPENDENCY_MISSING"]
}
```

Default gates must continue to pass without TurboVec installed.

Enablement requires an explicit config change under `[memory.semantic.backends.turbovec]` plus a separate production hardening review.
