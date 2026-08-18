# Codex Maintainer Workflow

## Purpose

ImperaOS is developed with extensive, end-to-end use of OpenAI Codex. Codex is an
engineering agent, not an authority boundary. Human review, tests, governance gates,
and release evidence remain authoritative.

## Current Development Loop

1. Define a scoped issue, failure, feature, or release goal.
2. Codex inspects the relevant code and proposes a plan or change.
3. Work on an isolated branch and worktree.
4. Add tests for behavior changes.
5. Run lint, targeted tests, and relevant ImperaOS governance/readiness gates.
6. Review security, compatibility, product-boundary, provenance, and documentation impact.
7. Merge only after required checks pass.
8. Preserve evidence required by release and qualification workflows.

## High-Value Maintainer Workloads

- Codebase orientation and issue reproduction/root-cause analysis
- Scoped implementation and refactoring
- Regression-test generation and PR patch review
- Documentation synchronization and compatibility audits
- Release-readiness and security-focused diff review
- Repetitive maintenance automation

## Intended API-Credit Use

Codex for OSS API credits would support project maintenance rather than ordinary
end-user inference: PR review and change-risk summaries, issue triage and reproduction
plans, regression-test proposals, documentation drift checks, release-readiness and
evidence review, security-sensitive diff analysis, and governed maintainer automation.

## Governance of Future Maintainer Automation

Read-only analysis may operate without mutation authority. Repository mutations remain
proposals or approval-gated actions. Sensitive content is redacted where applicable,
actions and decisions are auditable, and automation never bypasses CI, security,
policy, or release gates. Irreversible actions remain human-controlled.

This document does not imply OpenAI sponsorship, program acceptance, Codex Security
access, or an external audit.
