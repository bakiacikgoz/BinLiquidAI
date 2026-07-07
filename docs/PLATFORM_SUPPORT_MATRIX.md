# Platform Support Matrix

| Target | Tier | Claim Rule |
|---|---|---|
| `darwin-arm64` | supported if gate passes | Apple Silicon Mac evidence applies only to this target |
| `darwin-x64` | supported if gate passes | Requires separate Intel Mac evidence |
| `windows-x64` | supported if gate passes | Requires Windows x64 local evidence |
| `linux-x64` | supported if gate passes | Requires Linux x64 local evidence |
| `windows-arm64` | experimental | No supported claim without explicit evidence |
| `linux-arm64` | experimental | No supported claim without explicit evidence |
| other | unsupported | Product claim scope excludes it |

Use `uv run binliquid local-product matrix --profile enterprise --json` to see the current claim boundary.

