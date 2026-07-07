# Release Claim Set Boundary

`source-local-install` claims are generated only from verified platform evidence
for the current commit.

Allowed wording:

- `<target> source-local-install evidenced`

Disallowed wording without separate evidence:

- all platforms supported
- public signed installer ready
- unrestricted live computer-use ready
- public SaaS ready

If release text requests a target that is stale, blocked, or not evidenced, the
source install claim emits a no-ship blocker.
