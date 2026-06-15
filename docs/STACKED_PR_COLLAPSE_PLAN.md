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

After each human-approved merge, rerun the relevant local gate and keep force-push disabled.
