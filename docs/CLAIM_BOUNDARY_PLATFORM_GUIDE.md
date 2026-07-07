# Platform Claim Boundary Guide

The product capability statement is:

```text
Product capability = code support + dependency support + local or CI evidence + claim boundary
```

Do not turn one platform result into a universal CPU claim. If only `windows-x64` passed locally, then `darwin-arm64`, `darwin-x64`, and `linux-x64` remain `not_evidenced`.

No-ship blockers are reserved for false or overbroad claims, not for honest `not_evidenced` targets.

