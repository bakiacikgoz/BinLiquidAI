# Enterprise RBAC Canonical Roles

Enterprise workspace RBAC uses a small canonical role catalog so CLI, memory access, external gateway admission, and Operator Panel rendering evaluate the same permissions.

## Roles

`platform_admin` is the high-risk operator role. It can manage workspace state, memberships, enrollment tokens, approvals, and policy-sensitive operations.

`workspace_admin` can manage a workspace and enroll agents inside that workspace, but should not grant platform-wide authority.

`workspace_operator` can run governed operations and inspect workspace state.

`agent_operator` is used for enrolled agents and constrained automation principals. It should be paired with explicit enrollment and device binding.

`auditor` is read-only and can inspect evidence, snapshots, and membership state.

`viewer` is the lowest-risk human read-only role.

## Permission Rules

Permissions are additive across active memberships. Inactive memberships do not grant permissions. Unknown roles grant no permissions. High-risk roles must remain explicit in fixtures and tests so accidental privilege expansion is visible in review.

## Validation

Run the focused RBAC tests:

```powershell
uv run --extra dev pytest -q tests/test_enterprise_workspace_rbac.py tests/test_memory_enterprise_workspace_binding.py
```
