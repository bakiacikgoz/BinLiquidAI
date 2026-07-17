from __future__ import annotations

from collections.abc import Mapping

from imperaos.governance.approval_store import ApprovalStore
from imperaos.runtime.config import resolve_runtime_config


def resolve_artifact_approval_store(
    profile: str,
    *,
    env: Mapping[str, str] | None = None,
) -> ApprovalStore:
    """Resolve the single governance approval authority used by artifact runtimes."""

    config, _ = resolve_runtime_config(profile=profile, env=env)
    return ApprovalStore(config.governance.approval_store_path)
