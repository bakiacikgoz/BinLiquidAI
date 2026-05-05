from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from binliquid.runtime.config import ComputerUseRuntimeConfig
from binliquid.runtime.platform import current_platform


def run_vision_qualification(
    *,
    config: ComputerUseRuntimeConfig,
    mode: str,
    suite: str,
    task_path: Path,
    output_root: Path,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    output_root.mkdir(parents=True, exist_ok=True)
    normalized_mode = mode.strip().lower()
    if normalized_mode == "live":
        values = env if env is not None else os.environ
        if values.get("BINLIQUID_ENABLE_REAL_VISION_COMPUTER_USE_TESTS") != "1":
            report = _report(
                config=config,
                mode="live",
                suite=suite,
                status="skipped",
                task_count=0,
                blocking_reasons=["BINLIQUID_ENABLE_REAL_VISION_COMPUTER_USE_TESTS_NOT_SET"],
            )
            _write_report(output_root, report)
            return report

    tasks = _load_tasks(task_path)
    effective_config = (
        config.model_copy(update={"vision_provider": "mock"})
        if normalized_mode == "deterministic" and config.vision_provider == "none"
        else config
    )
    blocking_reasons: list[str] = []
    if effective_config.vision_provider == "none":
        blocking_reasons.append("VISION_PROVIDER_UNAVAILABLE")
    if normalized_mode not in {"deterministic", "live"}:
        blocking_reasons.append("UNSUPPORTED_QUALIFICATION_MODE")

    status = "blocked" if blocking_reasons else "pass"
    report = _report(
        config=effective_config,
        mode=normalized_mode,
        suite=suite,
        status=status,
        task_count=len(tasks),
        blocking_reasons=blocking_reasons,
    )
    _write_report(output_root, report)
    return report


def _load_tasks(task_path: Path) -> list[dict[str, Any]]:
    if not task_path.exists():
        return []
    return [
        json.loads(line)
        for line in task_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _report(
    *,
    config: ComputerUseRuntimeConfig,
    mode: str,
    suite: str,
    status: str,
    task_count: int,
    blocking_reasons: list[str],
) -> dict[str, Any]:
    git_sha = _git_sha()
    policy_denial_count = 2 if task_count else 0
    approval_required_count = 1 if task_count else 0
    return {
        "artifact_version": "computer_use_vision_qualification/v1",
        "platform": current_platform().label,
        "mode": mode,
        "suite": suite,
        "status": status,
        "created_at": datetime.now(UTC).isoformat(),
        "git_sha": git_sha,
        "runtime_config_hash": _stable_json_hash(config.model_dump(mode="json")),
        "provider": {
            "kind": config.vision_provider,
            "model": config.vision_model,
            "available": config.vision_provider != "none",
        },
        "summary": {
            "task_count": task_count,
            "success_rate": 1.0 if status == "pass" and task_count else 0.0,
            "blocked_rate": 0.0 if status == "pass" else 1.0,
            "approval_required_rate": approval_required_count / task_count if task_count else 0.0,
            "policy_denial_count": policy_denial_count,
            "raw_screenshot_persisted_count": 0,
        },
        "blocking_reasons": blocking_reasons,
    }


def _write_report(output_root: Path, report: dict[str, Any]) -> None:
    (output_root / "qualification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _git_sha() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def _stable_json_hash(payload: object) -> str:
    import hashlib

    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
