# Stacked PR Collapse Plan

The intended sequence remains:

```text
main
-> codex/workspace-memory-authority-v1
-> codex/semantic-memory-index-retrieval-quality-v1
-> codex/agent-memory-policy-enforcement-v1
-> codex/governed-pilot-workflow-release-closure-v1
-> codex/design-partner-target-evidence-attestation-closure-v1
-> codex/design-partner-rc-handoff-ops-readiness-v1
```

`codex/mainline-rc-freeze-stack-collapse-v1` adds verification and freeze evidence only. It does not collapse, merge, rebase, release, or deploy the stack.

`codex/rc-evidence-orchestrator-cross-platform-gates-v1` adds the hash-only RC gate evidence orchestrator for the same train. It proves that the Control Plane and Design Partner handoff gate artifacts are represented locally without performing the collapse, merge, release, or deploy.

After each human-approved merge, rerun the relevant local gate and keep force-push disabled.
