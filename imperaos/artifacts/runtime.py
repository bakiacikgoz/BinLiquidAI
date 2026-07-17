from __future__ import annotations

import os
from collections.abc import Mapping

from imperaos.artifacts.feature_flags import (
    ARTIFACT_FEATURE_FLAG_NAMES,
    resolve_artifact_feature_flags,
)
from imperaos.governance.approval_store import ApprovalStore
from imperaos.runtime.config import resolve_runtime_config

ARTIFACT_FEATURE_FLAG_ENV = {
    "artifact_workspace.enabled": "IMPERAOS_ARTIFACT_WORKSPACE_ENABLED",
    "artifact_workspace.document.enabled": "IMPERAOS_ARTIFACT_DOCUMENT_EDITOR_ENABLED",
    "artifact_workspace.form.enabled": "IMPERAOS_ARTIFACT_FORM_EDITOR_ENABLED",
    "artifact_workspace.code.enabled": "IMPERAOS_ARTIFACT_CODE_EDITOR_ENABLED",
    "artifact_workspace.flow.enabled": "IMPERAOS_ARTIFACT_FLOW_EDITOR_ENABLED",
    "artifact_workspace.spreadsheet.enabled": "IMPERAOS_ARTIFACT_SPREADSHEET_EDITOR_ENABLED",
    "artifact_workspace.canvas.enabled": "IMPERAOS_ARTIFACT_CANVAS_EDITOR_ENABLED",
    "artifact_workspace.slides.enabled": "IMPERAOS_ARTIFACT_SLIDES_EDITOR_ENABLED",
    "artifact_workspace.export.enabled": "IMPERAOS_ARTIFACT_EXPORT_ENABLED",
    "assistant_ui_runtime.enabled": "IMPERAOS_ASSISTANT_UI_RUNTIME_ENABLED",
    "ai_sdk_tauri_transport.enabled": "IMPERAOS_ASSISTANT_AI_SDK_RUNTIME_ENABLED",
}

if tuple(ARTIFACT_FEATURE_FLAG_ENV) != ARTIFACT_FEATURE_FLAG_NAMES:
    raise RuntimeError("artifact feature flag environment mapping drifted")


def resolve_artifact_approval_store(
    profile: str,
    *,
    env: Mapping[str, str] | None = None,
) -> ApprovalStore:
    """Resolve the single governance approval authority used by artifact runtimes."""

    config, _ = resolve_runtime_config(profile=profile, env=env)
    return ApprovalStore(config.governance.approval_store_path)


def resolve_runtime_artifact_feature_flags(
    *,
    env: Mapping[str, str] | None = None,
    license_capabilities: Mapping[str, bool] | None = None,
) -> dict[str, bool]:
    """Resolve backend-owned rollout authority from trusted process configuration."""

    environment = os.environ if env is None else env
    requested = {
        name: _enabled(environment.get(env_name))
        for name, env_name in ARTIFACT_FEATURE_FLAG_ENV.items()
    }
    return resolve_artifact_feature_flags(
        requested,
        license_capabilities=license_capabilities,
    )


def _enabled(value: str | None) -> bool:
    return value is not None and value.strip().lower() in {"1", "true", "yes", "on"}
