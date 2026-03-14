from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from binliquid.computer_use.actions import approval_snapshot_payload
from binliquid.computer_use.adapters import (
    BrowserAdapter,
    DesktopAdapter,
    FileDialogAdapter,
    SafariBrowserAdapter,
)
from binliquid.computer_use.guards import detect_hard_stop
from binliquid.computer_use.models import (
    ComputerUseMode,
    ComputerUseStopReason,
    ControlCommand,
    ControlCommandResult,
    EvidenceEnvelope,
    ExecutionStage,
    ExpectedFileOperation,
    ExpectedSurface,
    FileOperationMismatch,
    FileOperationObservation,
    PerceptionSnapshot,
    PerceptionSource,
    ProposedAction,
    RiskClass,
    SelectorContext,
    SessionExecutionState,
    SessionRequest,
    SurfaceMismatch,
    SurfaceObservation,
    VerificationResult,
    WindowState,
    WorldModel,
)
from binliquid.computer_use.perception import build_perception_fingerprint
from binliquid.computer_use.policy import BrowserAllowlistPolicy
from binliquid.computer_use.prompt_parser import parse_prompt_to_actions
from binliquid.computer_use.recorder import build_recorder_artifact
from binliquid.governance.runtime import GovernanceRuntime
from binliquid.runtime.config import RuntimeConfig
from binliquid.team.artifacts import (
    TeamArtifactPaths,
    ensure_team_artifact_paths,
    write_audit_envelope,
    write_handoffs,
    write_status,
    write_task_runs,
)
from binliquid.team.event_recorder import EventRecorder
from binliquid.team.models import JobRun, JobStatus, TeamEvent


class SessionCommand(StrEnum):
    RUN = "run"
    PAUSE = "pause"
    RESUME = "resume"
    STOP = "stop"


@dataclass(slots=True)
class ControlState:
    command: SessionCommand = SessionCommand.RUN
    updated_at: str = ""
    reason: str = ""
    pending_command: ControlCommand | None = None
    last_processed_command_id: str | None = None
    processed_command_ids: list[str] = field(default_factory=list)
    last_result: dict[str, Any] | None = None


class SessionControlBus:
    def __init__(self, job_dir: Path):
        self._path = job_dir / "control.json"
        self._history_path = job_dir / "control_history.jsonl"

    def write(
        self,
        command: SessionCommand,
        *,
        reason: str = "",
        issued_by: str | None = None,
        expected_state: str | None = None,
        command_id: str | None = None,
    ) -> ControlCommand:
        payload = self._load_payload()
        command_payload = ControlCommand(
            command_id=command_id or f"ctrl-{uuid4().hex[:12]}",
            command_type=command.value,
            issued_at=datetime.now(UTC).isoformat(),
            issued_by=issued_by,
            expected_state=expected_state,
            reason=reason or None,
        )
        payload["pending_command"] = command_payload.model_dump(mode="json")
        payload["updated_at"] = command_payload.issued_at
        self._save_payload(payload)
        return command_payload

    def read(self) -> ControlState:
        payload = self._load_payload()
        pending_payload = payload.get("pending_command")
        pending_command = (
            ControlCommand.model_validate(pending_payload) if pending_payload else None
        )
        return ControlState(
            command=(
                SessionCommand(pending_command.command_type)
                if pending_command is not None
                else SessionCommand.RUN
            ),
            updated_at=str(payload.get("updated_at") or ""),
            reason=str((pending_payload or {}).get("reason") or ""),
            pending_command=pending_command,
            last_processed_command_id=str(payload.get("last_processed_command_id") or "") or None,
            processed_command_ids=[
                str(item)
                for item in payload.get("processed_command_ids", [])
                if str(item)
            ],
            last_result=(
                dict(payload.get("last_result") or {})
                if isinstance(payload.get("last_result"), dict)
                else None
            ),
        )

    def clear(self) -> None:
        payload = self._load_payload()
        payload["pending_command"] = None
        payload["updated_at"] = datetime.now(UTC).isoformat()
        self._save_payload(payload)

    def mark_processed(
        self,
        result: ControlCommandResult,
        *,
        clear_pending: bool = True,
    ) -> None:
        payload = self._load_payload()
        processed = [
            str(item) for item in payload.get("processed_command_ids", []) if str(item)
        ]
        if result.command_id not in processed:
            processed.append(result.command_id)
        payload["processed_command_ids"] = processed[-32:]
        payload["last_processed_command_id"] = result.command_id
        payload["last_result"] = result.model_dump(mode="json")
        if clear_pending:
            pending = payload.get("pending_command") or {}
            if str(pending.get("command_id") or "") == result.command_id:
                payload["pending_command"] = None
        payload["updated_at"] = result.processed_at
        self._save_payload(payload)
        with self._history_path.open("a", encoding="utf-8") as file_obj:
            file_obj.write(json.dumps(result.model_dump(mode="json"), ensure_ascii=False) + "\n")

    def history(self) -> list[dict[str, Any]]:
        if not self._history_path.exists():
            return []
        return [
            json.loads(line)
            for line in self._history_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

    def _load_payload(self) -> dict[str, Any]:
        if not self._path.exists():
            return {
                "pending_command": None,
                "updated_at": "",
                "last_processed_command_id": None,
                "processed_command_ids": [],
                "last_result": None,
            }
        payload = json.loads(self._path.read_text(encoding="utf-8"))
        payload.setdefault("pending_command", None)
        payload.setdefault("updated_at", "")
        payload.setdefault("last_processed_command_id", None)
        payload.setdefault("processed_command_ids", [])
        payload.setdefault("last_result", None)
        return payload

    def _save_payload(self, payload: dict[str, Any]) -> None:
        self._path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


_STATE_TRANSITIONS: dict[SessionExecutionState, set[SessionExecutionState]] = {
    SessionExecutionState.QUEUED: {SessionExecutionState.STARTING},
    SessionExecutionState.STARTING: {
        SessionExecutionState.RUNNING,
        SessionExecutionState.PAUSING,
        SessionExecutionState.STOPPING,
        SessionExecutionState.STOPPED,
        SessionExecutionState.FAILED,
    },
    SessionExecutionState.RUNNING: {
        SessionExecutionState.PAUSING,
        SessionExecutionState.STOPPING,
        SessionExecutionState.AWAITING_APPROVAL,
        SessionExecutionState.COMPLETED,
        SessionExecutionState.FAILED,
    },
    SessionExecutionState.PAUSING: {
        SessionExecutionState.PAUSED,
        SessionExecutionState.STOPPING,
        SessionExecutionState.FAILED,
    },
    SessionExecutionState.PAUSED: {
        SessionExecutionState.RESUMING,
        SessionExecutionState.STOPPING,
        SessionExecutionState.FAILED,
    },
    SessionExecutionState.RESUMING: {
        SessionExecutionState.RUNNING,
        SessionExecutionState.STOPPING,
        SessionExecutionState.FAILED,
    },
    SessionExecutionState.STOPPING: {
        SessionExecutionState.STOPPED,
        SessionExecutionState.FAILED,
    },
    SessionExecutionState.STOPPED: set(),
    SessionExecutionState.AWAITING_APPROVAL: {
        SessionExecutionState.RESUMING,
        SessionExecutionState.RUNNING,
        SessionExecutionState.STOPPING,
        SessionExecutionState.STOPPED,
        SessionExecutionState.FAILED,
    },
    SessionExecutionState.COMPLETED: set(),
    SessionExecutionState.FAILED: set(),
}
_TERMINAL_SESSION_STATES = {
    SessionExecutionState.STOPPED,
    SessionExecutionState.COMPLETED,
    SessionExecutionState.FAILED,
}
_STATE_TARGETS_BY_COMMAND: dict[SessionCommand, set[SessionExecutionState]] = {
    SessionCommand.PAUSE: {
        SessionExecutionState.PAUSING,
        SessionExecutionState.PAUSED,
    },
    SessionCommand.RESUME: {
        SessionExecutionState.RESUMING,
    },
    SessionCommand.STOP: {
        SessionExecutionState.STOPPING,
        SessionExecutionState.STOPPED,
    },
}


class SessionRegistry:
    def __init__(self, path: str | Path):
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {"sessions": {}}
        return json.loads(self._path.read_text(encoding="utf-8"))

    def _save(self, payload: dict[str, Any]) -> None:
        self._path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def register(self, *, job_id: str, job_dir: Path, state: str) -> None:
        payload = self._load()
        sessions = payload.setdefault("sessions", {})
        sessions[job_id] = {
            "job_id": job_id,
            "job_dir": str(job_dir),
            "pid": os.getpid(),
            "state": state,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        self._save(payload)

    def update(self, *, job_id: str, state: str) -> None:
        payload = self._load()
        sessions = payload.setdefault("sessions", {})
        if job_id in sessions:
            sessions[job_id]["state"] = state
            sessions[job_id]["updated_at"] = datetime.now(UTC).isoformat()
        self._save(payload)

    def remove(self, *, job_id: str) -> None:
        payload = self._load()
        payload.setdefault("sessions", {}).pop(job_id, None)
        self._save(payload)

    def get(self, *, job_id: str) -> dict[str, Any] | None:
        payload = self._load()
        return payload.setdefault("sessions", {}).get(job_id)


@dataclass(slots=True)
class RuntimeAdapters:
    browser: BrowserAdapter
    desktop: DesktopAdapter
    dialog: FileDialogAdapter


class ComputerUseRunner:
    def __init__(
        self,
        *,
        config: RuntimeConfig,
        root_dir: str | Path | None = None,
        adapters: RuntimeAdapters | None = None,
        registry: SessionRegistry | None = None,
    ) -> None:
        self._config = config
        self._root_dir = Path(root_dir or config.team.artifact_dir)
        allowed_roots = [
            Path.cwd(),
            Path(config.workspace_root).expanduser(),
            self._root_dir,
            Path.home().joinpath("Downloads"),
            Path("/tmp"),
        ]
        runtime_adapters = adapters or RuntimeAdapters(
            desktop=DesktopAdapter(),
            dialog=FileDialogAdapter(allowed_roots=allowed_roots),
            browser=SafariBrowserAdapter(
                desktop_adapter=DesktopAdapter(),
                dialog_adapter=FileDialogAdapter(allowed_roots=allowed_roots),
            ),
        )
        self._adapters = runtime_adapters
        self._registry = registry or SessionRegistry(
            self._root_dir.parent / "computer_use_registry.json"
        )
        self._governance = GovernanceRuntime(config=config)

    def _execution_state(self, state: dict[str, Any]) -> SessionExecutionState:
        raw = str(
            state.get("session_state")
            or state.get("lifecycle_state")
            or SessionExecutionState.STARTING.value
        )
        return SessionExecutionState(raw)

    def _set_execution_state(
        self,
        state: dict[str, Any],
        new_state: SessionExecutionState,
    ) -> None:
        current = self._execution_state(state)
        if current != new_state and new_state not in _STATE_TRANSITIONS.get(current, set()):
            raise RuntimeError(
                f"invalid session state transition: {current.value} -> {new_state.value}"
            )
        state["session_state"] = new_state.value
        state["lifecycle_state"] = new_state.value
        state["paused"] = new_state == SessionExecutionState.PAUSED
        state["stopped"] = new_state == SessionExecutionState.STOPPED
        state["resume_allowed"] = new_state == SessionExecutionState.PAUSED

    def _control_target_state(
        self,
        *,
        command: SessionCommand,
        current: SessionExecutionState,
    ) -> SessionExecutionState | None:
        if command == SessionCommand.PAUSE:
            if current in {SessionExecutionState.RUNNING, SessionExecutionState.STARTING}:
                return SessionExecutionState.PAUSING
            if current in _STATE_TARGETS_BY_COMMAND[command]:
                return current
            return None
        if command == SessionCommand.RESUME:
            if current in {SessionExecutionState.PAUSED, SessionExecutionState.AWAITING_APPROVAL}:
                return SessionExecutionState.RESUMING
            if current in _STATE_TARGETS_BY_COMMAND[command]:
                return current
            return None
        if command == SessionCommand.STOP:
            if current in {
                SessionExecutionState.RUNNING,
                SessionExecutionState.PAUSING,
                SessionExecutionState.PAUSED,
                SessionExecutionState.AWAITING_APPROVAL,
                SessionExecutionState.STARTING,
                SessionExecutionState.RESUMING,
            }:
                return SessionExecutionState.STOPPING
            if current in _STATE_TARGETS_BY_COMMAND[command]:
                return current
            return None
        return None

    def _control_outcome(
        self,
        *,
        command: SessionCommand,
        current: SessionExecutionState,
    ) -> str:
        target_state = self._control_target_state(command=command, current=current)
        if target_state is None:
            return "rejected"
        if current in _STATE_TARGETS_BY_COMMAND[command]:
            return "already_applied"
        return "accepted"

    def _set_pending_control(
        self,
        *,
        state: dict[str, Any],
        command: ControlCommand | None,
    ) -> None:
        state["pending_command"] = (
            command.model_dump(mode="json") if command is not None else None
        )
        state["last_control_command"] = (
            command.model_dump(mode="json")
            if command is not None
            else state.get("last_control_command")
        )

    def _set_last_control_result(
        self,
        *,
        state: dict[str, Any],
        result: ControlCommandResult,
    ) -> None:
        state["last_control_result"] = result.model_dump(mode="json")
        state["last_processed_command_id"] = result.command_id
        if result.outcome in {"applied", "rejected", "already_applied"}:
            state["pending_command"] = None

    def _build_control_result(
        self,
        *,
        command: ControlCommand,
        outcome: str,
        previous_state: SessionExecutionState,
        resulting_state: SessionExecutionState,
        reason: str | None = None,
        deferred_until_safe_checkpoint: bool = False,
    ) -> ControlCommandResult:
        return ControlCommandResult(
            command_id=command.command_id,
            command_type=command.command_type,
            outcome=outcome,
            processed_at=datetime.now(UTC).isoformat(),
            previous_state=previous_state.value,
            resulting_state=resulting_state.value,
            reason=reason,
            deferred_until_safe_checkpoint=deferred_until_safe_checkpoint,
        )

    def _load_status_artifact(self, *, paths: TeamArtifactPaths) -> dict[str, Any]:
        if not paths.status_path.exists():
            return {}
        return json.loads(paths.status_path.read_text(encoding="utf-8"))

    def _write_existing_status(self, *, paths: TeamArtifactPaths, payload: dict[str, Any]) -> None:
        if not payload:
            return
        write_status(
            paths,
            {
                key: value
                for key, value in payload.items()
                if key != "contract_version"
            },
        )

    def _emit_artifact_event(
        self,
        *,
        paths: TeamArtifactPaths,
        job_payload: dict[str, Any],
        event: str,
        status_before: str | None,
        status_after: str | None,
        data: dict[str, Any],
    ) -> None:
        recorder = EventRecorder(
            paths=paths,
            team_id=str(job_payload.get("team_id") or "aegis-computer-use"),
            case_id=str(
                job_payload.get("case_id")
                or f"case-{job_payload.get('job_id') or 'unknown'}"
            ),
            job_id=str(job_payload.get("job_id") or ""),
            sink=[],
            lock=threading.Lock(),
        )
        recorder.emit(
            event,
            phase="computer_use",
            status_before=status_before,
            status_after=status_after,
            data=data,
        )

    def _apply_control_artifact_state(
        self,
        *,
        computer_use: dict[str, Any],
        session_state: SessionExecutionState,
        pending_command: ControlCommand | None,
        result: ControlCommandResult | None = None,
        stopped_by_user: bool | None = None,
    ) -> None:
        computer_use["session_state"] = session_state.value
        computer_use["lifecycle_state"] = session_state.value
        computer_use["paused"] = session_state == SessionExecutionState.PAUSED
        computer_use["stopped"] = session_state == SessionExecutionState.STOPPED
        computer_use["resume_allowed"] = session_state == SessionExecutionState.PAUSED
        computer_use["pending_command"] = (
            pending_command.model_dump(mode="json") if pending_command is not None else None
        )
        if pending_command is not None:
            computer_use["last_control_command"] = pending_command.model_dump(mode="json")
        if result is not None:
            computer_use["last_control_result"] = result.model_dump(mode="json")
            computer_use["last_processed_command_id"] = result.command_id
        if stopped_by_user is not None:
            computer_use["stopped_by_user"] = stopped_by_user

    def _approval_ready(self, approval_id: str) -> bool:
        if not approval_id:
            return False
        ticket = self._governance.approval_store.get(approval_id)
        return ticket is not None and ticket.execution_status.value == "executed"

    def _build_recovery_state(
        self,
        *,
        job_id: str,
        emit_event: bool,
    ) -> dict[str, Any]:
        paths = ensure_team_artifact_paths(job_id=job_id, root_dir=self._root_dir)
        artifact = self._load_status_artifact(paths=paths)
        if not artifact:
            raise FileNotFoundError(f"job not found: {job_id}")
        computer_use = dict(artifact.get("computer_use") or {})
        job_payload = dict(artifact.get("job") or {"job_id": job_id})
        session_state = SessionExecutionState(
            str(
                computer_use.get("session_state")
                or computer_use.get("lifecycle_state")
                or SessionExecutionState.RUNNING.value
            )
        )
        approval_id = str(computer_use.get("pending_approval_id") or "")
        resume_allowed = session_state == SessionExecutionState.PAUSED or (
            session_state == SessionExecutionState.AWAITING_APPROVAL
            and self._approval_ready(approval_id)
        )
        control = SessionControlBus(paths.job_dir)
        control_state = control.read()
        last_completed_action_index = max(
            (
                index
                for index, action in enumerate(computer_use.get("actions", []))
                if str(action.get("status") or "") == "verified"
            ),
            default=-1,
        )
        recovery = {
            "recoverable_state": session_state.value,
            "last_processed_command_id": str(
                computer_use.get("last_processed_command_id")
                or control_state.last_processed_command_id
                or ""
            )
            or None,
            "last_completed_action_index": last_completed_action_index,
            "pending_control_command": (
                control_state.pending_command.model_dump(mode="json")
                if control_state.pending_command is not None
                else None
            ),
            "resume_allowed": resume_allowed,
            "control_history": control.history(),
        }
        computer_use["resume_allowed"] = resume_allowed
        artifact["computer_use"] = computer_use
        self._write_existing_status(paths=paths, payload=artifact)
        if emit_event:
            event_name = (
                "computer_use.recovery_loaded"
                if session_state
                in {
                    SessionExecutionState.PAUSED,
                    SessionExecutionState.AWAITING_APPROVAL,
                    SessionExecutionState.STOPPED,
                    SessionExecutionState.COMPLETED,
                    SessionExecutionState.FAILED,
                }
                else "computer_use.recovery_not_resumable"
            )
            self._emit_artifact_event(
                paths=paths,
                job_payload=job_payload,
                event=event_name,
                status_before=job_payload.get("status"),
                status_after=job_payload.get("status"),
                data=recovery,
            )
        return recovery

    def run(
        self,
        *,
        prompt: str,
        job_id: str,
        case_id: str | None = None,
        mode: ComputerUseMode = ComputerUseMode.EXECUTE,
    ) -> dict[str, Any]:
        family, actions = parse_prompt_to_actions(prompt=prompt, mode=mode)
        request = SessionRequest(
            run_id=job_id,
            prompt=prompt,
            mode=mode,
            task_family=family,
            allowlisted_domains=_allowlisted_domains(actions),
        )
        paths = ensure_team_artifact_paths(job_id=job_id, root_dir=self._root_dir)
        events: list[TeamEvent] = []
        recorder = EventRecorder(
            paths=paths,
            team_id="aegis-computer-use",
            case_id=case_id or f"case-{job_id}",
            job_id=job_id,
            sink=events,
            lock=threading.Lock(),
        )
        control = SessionControlBus(paths.job_dir)
        control.clear()
        self._registry.register(
            job_id=job_id,
            job_dir=paths.job_dir,
            state=SessionExecutionState.STARTING.value,
        )

        job = JobRun(
            job_id=job_id,
            case_id=case_id or f"case-{job_id}",
            team_id="aegis-computer-use",
            request=prompt,
            status=JobStatus.RUNNING,
        )
        policy = BrowserAllowlistPolicy(allowlisted_domains=request.allowlisted_domains)
        state: dict[str, Any] = {
            "mode": mode.value,
            "task_family": family.value,
            "lifecycle_state": SessionExecutionState.STARTING.value,
            "session_state": SessionExecutionState.STARTING.value,
            "stage": ExecutionStage.PLAN.value,
            "active_action": None,
            "current_url": None,
            "active_app": None,
            "active_window": None,
            "foreground_app": None,
            "focused_window_title": None,
            "browser_tab_title": None,
            "active_surface": None,
            "expected_surface": None,
            "observed_surface": None,
            "surface_mismatch": None,
            "expected_file_operation": None,
            "observed_file_operation": None,
            "file_operation_mismatch": None,
            "pending_approval_id": None,
            "paused": False,
            "stopped": False,
            "stopped_by_user": False,
            "last_verified_effect": None,
            "last_verification_result": {},
            "last_error": None,
            "last_control_command": None,
            "last_control_result": None,
            "last_processed_command_id": None,
            "pending_command": None,
            "resume_allowed": False,
            "last_safe_checkpoint": None,
            "artifacts": {},
            "actions": [],
        }
        write_task_runs(paths, [])
        write_handoffs(paths, [])
        recorder.emit(
            "team_start",
            phase="team",
            status_before="pending",
            status_after="running",
            data={"request": prompt},
        )
        recorder.emit(
            "session_started",
            phase="computer_use",
            status_before="pending",
            status_after="running",
            data={"mode": mode.value, "action_count": len(actions)},
        )
        self._set_execution_state(state, SessionExecutionState.RUNNING)
        self._registry.update(job_id=job_id, state=SessionExecutionState.RUNNING.value)
        self._write_runtime_status(
            paths=paths,
            job=job,
            state=state,
            events=events,
            actions=actions,
        )

        try:
            for action in actions:
                self._cooperative_check(
                    job=job,
                    state=state,
                    recorder=recorder,
                    control=control,
                    paths=paths,
                    events=events,
                    actions=actions,
                    checkpoint="before_action",
                )
                state["stage"] = ExecutionStage.OBSERVE.value
                expected_surface = self._derive_expected_surface(action=action, state=state)
                observed_surface = self._observe_surface(action=action)
                self._store_surface_state(
                    state=state,
                    expected_surface=expected_surface,
                    observed_surface=observed_surface,
                    surface_mismatch=None,
                )
                state["stage"] = ExecutionStage.COMPARE_STATE.value
                state["active_action"] = action.action_id
                expected_file_operation = self._derive_expected_file_operation(action=action)
                observed_file_operation = (
                    self._observe_file_operation(
                        action=action,
                        expected_file_operation=expected_file_operation,
                        use_execution_result=False,
                    )
                    if expected_file_operation is not None
                    else None
                )
                self._store_file_operation_state(
                    state=state,
                    expected_file_operation=expected_file_operation,
                    observed_file_operation=observed_file_operation,
                    file_operation_mismatch=None,
                )
                state["actions"].append(
                    {
                        "action_id": action.action_id,
                        "target_ref": action.target_descriptor.target_ref,
                        "status": "planned",
                    }
                )
                recorder.emit(
                    "action_planned",
                    phase="computer_use",
                    status_before=job.status.value,
                    status_after=job.status.value,
                    data={
                        **_action_payload(action),
                        "expected_surface": expected_surface.model_dump(mode="json"),
                        "observed_surface": observed_surface.model_dump(mode="json"),
                        "expected_file_operation": (
                            expected_file_operation.model_dump(mode="json")
                            if expected_file_operation is not None
                            else None
                        ),
                        "observed_file_operation": (
                            observed_file_operation.model_dump(mode="json")
                            if observed_file_operation is not None
                            else None
                        ),
                    },
                )
                self._write_runtime_status(
                    paths=paths,
                    job=job,
                    state=state,
                    events=events,
                    actions=actions,
                )
                surface_verification = self._verify_surface(
                    expected_surface=expected_surface,
                    observed_surface=observed_surface,
                )
                if not surface_verification.verified:
                    state["actions"][-1]["status"] = "surface_mismatch"
                    state["actions"][-1]["verification"] = surface_verification.model_dump(
                        mode="json"
                    )
                    self._surface_fail_closed(
                        action=action,
                        verification=surface_verification,
                        job=job,
                        state=state,
                        recorder=recorder,
                        paths=paths,
                        events=events,
                        actions=actions,
                    )
                    return self._status_payload(job=job, state=state)

                if expected_file_operation is not None and observed_file_operation is not None:
                    file_precheck = self._verify_file_operation(
                        expected_file_operation=expected_file_operation,
                        observed_file_operation=observed_file_operation,
                        executed=False,
                    )
                    if not file_precheck.verified:
                        state["actions"][-1]["status"] = "file_operation_mismatch"
                        state["actions"][-1]["verification"] = file_precheck.model_dump(
                            mode="json"
                        )
                        self._file_operation_fail_closed(
                            action=action,
                            verification=file_precheck,
                            job=job,
                            state=state,
                            recorder=recorder,
                            paths=paths,
                            events=events,
                            actions=actions,
                        )
                        return self._status_payload(job=job, state=state)

                perception = self._inspect_action(action)
                state["active_app"] = perception.app_identity
                state["active_window"] = perception.window_or_tab_identity
                state["current_url"] = perception.current_url
                title = str((perception.evidence.accessibility_subset or {}).get("title") or "")
                if title:
                    state["browser_tab_title"] = title
                recorder.emit(
                    "observation_captured",
                    phase="computer_use",
                    status_before=job.status.value,
                    status_after=job.status.value,
                    snapshot_hash=perception.perception_fingerprint,
                    data={
                        "action_id": action.action_id,
                        "current_url": perception.current_url,
                        "window_identity": perception.window_or_tab_identity,
                        "expected_surface": expected_surface.model_dump(mode="json"),
                        "observed_surface": observed_surface.model_dump(mode="json"),
                        "expected_file_operation": (
                            expected_file_operation.model_dump(mode="json")
                            if expected_file_operation is not None
                            else None
                        ),
                    },
                )
                stop_reason = (
                    detect_hard_stop(
                        snapshot=perception,
                        policy=policy,
                        expected_url=str(
                            action.parameters.get("url") or action.target_descriptor.current_url
                        )
                        or None,
                    )
                    if action.app_identity.startswith("browser:")
                    else (
                        ComputerUseStopReason.UNEXPECTED_MODAL
                        if perception.unexpected_modal
                        else ComputerUseStopReason.FOCUS_DRIFT
                        if not perception.focused and action.action_id != "launch_app"
                        else None
                    )
                )
                if stop_reason is not None:
                    state["actions"][-1]["status"] = "failed"
                    self._hard_stop(
                        stop_reason=stop_reason,
                        action=action,
                        job=job,
                        state=state,
                        recorder=recorder,
                        paths=paths,
                        events=events,
                        actions=actions,
                        policy=policy,
                        perception=perception,
                    )
                    return self._status_payload(job=job, state=state)

                state["stage"] = ExecutionStage.DECIDE_ACTION.value
                self._write_runtime_status(
                    paths=paths,
                    job=job,
                    state=state,
                    events=events,
                    actions=actions,
                    policy=policy,
                    perception=perception,
                )

                if self._requires_approval(request=request, action=action):
                    ticket = self._request_approval(
                        request=request,
                        action=action,
                        perception=perception,
                        policy=policy,
                        recorder=recorder,
                        job=job,
                        state=state,
                        paths=paths,
                        events=events,
                        actions=actions,
                    )
                    self._wait_until_resumed(
                        control=control,
                        ticket_id=ticket,
                        job=job,
                        state=state,
                        recorder=recorder,
                        paths=paths,
                        events=events,
                        actions=actions,
                    )

                recorder.emit(
                    "action_started",
                    phase="computer_use",
                    status_before=job.status.value,
                    status_after=job.status.value,
                    data=_action_payload(action),
                )
                state["stage"] = ExecutionStage.EXECUTE.value
                action.execution_result = self._execute_action(action)
                self._apply_execution_result(state=state, action=action)
                self._cooperative_check(
                    job=job,
                    state=state,
                    recorder=recorder,
                    control=control,
                    paths=paths,
                    events=events,
                    actions=actions,
                    checkpoint="after_execute",
                )

                verification = self._verify_action(action=action, before=perception)
                if not verification.verified:
                    action.execution_result = self._execute_action(action)
                    self._apply_execution_result(state=state, action=action)
                    verification = self._verify_action(action=action, before=perception)
                file_verification = None
                if expected_file_operation is not None:
                    observed_file_operation = self._observe_file_operation(
                        action=action,
                        expected_file_operation=expected_file_operation,
                        use_execution_result=True,
                    )
                    file_verification = self._verify_file_operation(
                        expected_file_operation=expected_file_operation,
                        observed_file_operation=observed_file_operation,
                        executed=True,
                    )
                    self._store_file_operation_state(
                        state=state,
                        expected_file_operation=expected_file_operation,
                        observed_file_operation=observed_file_operation,
                        file_operation_mismatch=file_verification.file_operation_mismatch,
                    )
                    verification = self._merge_verification_results(
                        primary=verification,
                        secondary=file_verification,
                    )
                if not verification.verified:
                    state["last_error"] = verification.mismatch_code or verification.summary
                    state["last_verification_result"] = verification.model_dump(mode="json")
                    state["actions"][-1]["status"] = "failed"
                    state["actions"][-1]["verification"] = verification.model_dump(mode="json")
                    if (
                        file_verification is not None
                        and file_verification.file_operation_mismatch is not None
                    ):
                        self._file_operation_fail_closed(
                            action=action,
                            verification=verification,
                            job=job,
                            state=state,
                            recorder=recorder,
                            paths=paths,
                            events=events,
                            actions=actions,
                        )
                        return self._status_payload(job=job, state=state)
                    recorder.emit(
                        "action_failed",
                        phase="computer_use",
                        status_before=job.status.value,
                        status_after=JobStatus.FAILED.value,
                        data={
                            **_action_payload(action),
                            "verification": verification.model_dump(mode="json"),
                        },
                    )
                    job.status = JobStatus.FAILED
                    job.finished_at = datetime.now(UTC)
                    job.final_output = "computer-use session failed"
                    self._set_execution_state(state, SessionExecutionState.FAILED)
                    self._write_runtime_status(
                        paths=paths,
                        job=job,
                        state=state,
                        events=events,
                        actions=actions,
                    )
                    break

                state["last_verified_effect"] = action.expected_effect
                state["last_verification_result"] = verification.model_dump(mode="json")
                state["stage"] = ExecutionStage.VERIFY.value
                state["actions"][-1]["status"] = "verified"
                state["actions"][-1]["verification"] = verification.model_dump(mode="json")
                self._record_file_artifacts(
                    state=state,
                    action=action,
                    file_verification=file_verification,
                )
                post_surface = self._observe_surface(action=action)
                self._store_surface_state(
                    state=state,
                    expected_surface=expected_surface,
                    observed_surface=post_surface,
                    surface_mismatch=None,
                )
                if file_verification is not None:
                    artifact_path = (
                        str(action.execution_result.get("download_path") or "")
                        or str(action.execution_result.get("selected_file") or "")
                    )
                    recorder.emit(
                        "computer_use.file_operation_verified",
                        phase="computer_use",
                        status_before=job.status.value,
                        status_after=job.status.value,
                        data={
                            **_action_payload(action),
                            "artifact_path": artifact_path or None,
                            "expected_file_operation": (
                                file_verification.expected_file_operation.model_dump(mode="json")
                                if file_verification.expected_file_operation is not None
                                else {}
                            ),
                            "observed_file_operation": (
                                file_verification.observed_file_operation.model_dump(mode="json")
                                if file_verification.observed_file_operation is not None
                                else {}
                            ),
                            "verification": file_verification.model_dump(mode="json"),
                        },
                    )
                recorder.emit(
                    "action_verified",
                    phase="computer_use",
                    status_before=job.status.value,
                    status_after=job.status.value,
                    data={
                        **_action_payload(action),
                        "verification": verification.model_dump(mode="json"),
                    },
                )
                self._write_runtime_status(
                    paths=paths,
                    job=job,
                    state=state,
                    events=events,
                    actions=actions,
                    policy=policy,
                    perception=perception,
                )
                self._cooperative_check(
                    job=job,
                    state=state,
                    recorder=recorder,
                    control=control,
                    paths=paths,
                    events=events,
                    actions=actions,
                    checkpoint="after_verify",
                )

            if job.status == JobStatus.RUNNING:
                job.status = JobStatus.COMPLETED
                job.finished_at = datetime.now(UTC)
                job.final_output = "computer-use session completed"
                self._set_execution_state(state, SessionExecutionState.COMPLETED)
                state["stage"] = ExecutionStage.COMPLETED.value
                recorder.emit(
                    "session_completed",
                    phase="computer_use",
                    status_before=JobStatus.RUNNING.value,
                    status_after=JobStatus.COMPLETED.value,
                    data={"action_count": len(actions)},
                )
                self._write_runtime_status(
                    paths=paths,
                    job=job,
                    state=state,
                    events=events,
                    actions=actions,
                )
            return self._status_payload(job=job, state=state)
        finally:
            self._finalize(paths=paths, job=job, events=events)
            self._registry.remove(job_id=job.job_id)

    def session_state(self, *, job_id: str) -> dict[str, Any]:
        entry = self._registry.get(job_id=job_id)
        job_dir = self._root_dir / job_id
        status_path = job_dir / "status.json"
        if status_path.exists():
            status = json.loads(status_path.read_text(encoding="utf-8"))
            recovery = self._build_recovery_state(job_id=job_id, emit_event=False)
            return {
                "job_id": job_id,
                "registry": entry,
                "computer_use": status.get("computer_use", {}),
                "job": status.get("job", {}),
                "recovery": recovery,
            }
        return {
            "job_id": job_id,
            "registry": entry,
            "computer_use": {},
            "job": {},
            "recovery": {},
        }

    def load_recovery_state(self, *, job_id: str) -> dict[str, Any]:
        return self._build_recovery_state(job_id=job_id, emit_event=True)

    def request_control(self, *, job_id: str, command: SessionCommand) -> dict[str, Any]:
        job_dir = self._root_dir / job_id
        if not job_dir.exists():
            raise FileNotFoundError(f"job not found: {job_id}")
        paths = ensure_team_artifact_paths(job_id=job_id, root_dir=self._root_dir)
        control = SessionControlBus(job_dir)
        artifact = self._load_status_artifact(paths=paths)
        computer_use = dict(artifact.get("computer_use") or {})
        job_payload = dict(
            artifact.get("job")
            or {
                "job_id": job_id,
                "case_id": f"case-{job_id}",
                "team_id": "aegis-computer-use",
                "status": JobStatus.RUNNING.value,
            }
        )
        current_state = SessionExecutionState(
            str(
                computer_use.get("session_state")
                or computer_use.get("lifecycle_state")
                or SessionExecutionState.RUNNING.value
            )
        )
        existing = control.read().pending_command
        approval_id = str(computer_use.get("pending_approval_id") or "")
        approval_ready = False
        if approval_id:
            ticket = self._governance.approval_store.get(approval_id)
            approval_ready = ticket is not None and ticket.execution_status.value == "executed"

        if (
            command == SessionCommand.RESUME
            and current_state == SessionExecutionState.AWAITING_APPROVAL
        ):
            if not approval_ready:
                outcome = "rejected"
                reason = "approval_not_executed"
                target_state = current_state
            else:
                outcome = "accepted"
                reason = "approval_executed"
                target_state = SessionExecutionState.RESUMING
        else:
            outcome = self._control_outcome(command=command, current=current_state)
            reason = None
            target_state = self._control_target_state(command=command, current=current_state)
            if target_state is None:
                target_state = current_state
                reason = f"{command.value}_not_allowed_from_{current_state.value}"

        if existing is not None and existing.command_type == command.value:
            outcome = "already_applied"
            target_state = current_state
            reason = f"{command.value}_already_pending"

        command_payload = ControlCommand(
            command_id=f"ctrl-{uuid4().hex[:12]}",
            command_type=command.value,
            issued_at=datetime.now(UTC).isoformat(),
            issued_by="operator",
            expected_state=current_state.value,
            reason=reason,
        )
        self._emit_artifact_event(
            paths=paths,
            job_payload=job_payload,
            event="computer_use.control_command_received",
            status_before=job_payload.get("status"),
            status_after=job_payload.get("status"),
            data={
                "command": command_payload.model_dump(mode="json"),
                "session_state": current_state.value,
            },
        )
        if outcome == "accepted":
            pending_command = control.write(
                command,
                reason=reason or "",
                issued_by="operator",
                expected_state=current_state.value,
                command_id=command_payload.command_id,
            )
            self._apply_control_artifact_state(
                computer_use=computer_use,
                session_state=target_state,
                pending_command=pending_command,
            )
            artifact["computer_use"] = computer_use
            self._write_existing_status(paths=paths, payload=artifact)
            self._registry.update(job_id=job_id, state=target_state.value)
            return {
                "job_id": job_id,
                "requested": command.value,
                "command_id": pending_command.command_id,
                "outcome": outcome,
            }

        result = self._build_control_result(
            command=command_payload,
            outcome=outcome,
            previous_state=current_state,
            resulting_state=current_state,
            reason=reason,
        )
        control.mark_processed(result, clear_pending=False)
        self._apply_control_artifact_state(
            computer_use=computer_use,
            session_state=current_state,
            pending_command=(
                existing
                if outcome == "already_applied" and existing is not None
                else None
            ),
            result=result,
            stopped_by_user=bool(computer_use.get("stopped_by_user")),
        )
        computer_use["last_control_command"] = command_payload.model_dump(mode="json")
        artifact["computer_use"] = computer_use
        self._write_existing_status(paths=paths, payload=artifact)
        if outcome == "rejected":
            self._emit_artifact_event(
                paths=paths,
                job_payload=job_payload,
                event="computer_use.control_command_rejected",
                status_before=job_payload.get("status"),
                status_after=job_payload.get("status"),
                data={
                    "command": command_payload.model_dump(mode="json"),
                    "result": result.model_dump(mode="json"),
                },
            )
        self._registry.update(job_id=job_id, state=current_state.value)
        return {
            "job_id": job_id,
            "requested": command.value,
            "command_id": command_payload.command_id,
            "outcome": outcome,
            "reason": reason,
        }

    def _select_adapter(self, action: ProposedAction) -> BrowserAdapter:
        if action.app_identity.startswith("browser:"):
            return self._adapters.browser
        raise RuntimeError(f"unsupported adapter for {action.app_identity}")

    def _observe_surface(self, *, action: ProposedAction) -> SurfaceObservation:
        desktop_surface = self._adapters.desktop.observe_surface()
        if action.app_identity.startswith("browser:"):
            browser_surface = self._select_adapter(action).observe_surface(
                target=action.target_descriptor
            )
            return SurfaceObservation(
                foreground_app=desktop_surface.foreground_app or browser_surface.foreground_app,
                bundle_id=desktop_surface.bundle_id or browser_surface.bundle_id,
                focused_window_title=(
                    desktop_surface.focused_window_title or browser_surface.focused_window_title
                ),
                active_tab_url=browser_surface.active_tab_url,
                active_tab_title=browser_surface.active_tab_title,
                modal_detected=desktop_surface.modal_detected or browser_surface.modal_detected,
                visible_selectors=browser_surface.visible_selectors,
                captured_at=browser_surface.captured_at,
            )
        return desktop_surface

    def _derive_expected_surface(
        self,
        *,
        action: ProposedAction,
        state: dict[str, Any],
    ) -> ExpectedSurface:
        if action.app_identity.startswith("browser:"):
            current_url = str(state.get("current_url") or "")
            expected = ExpectedSurface(
                app_name="Safari",
                bundle_id="com.apple.Safari",
                allow_modal=False,
            )
            if (
                action.action_id not in {"open_url", "switch_tab"}
                and current_url.startswith(("http://", "https://"))
                and current_url != "about:blank"
            ):
                parsed = urlparse(current_url)
                expected.tab_url_host = parsed.netloc or None
                expected.tab_url_prefix = _normalized_url_prefix(current_url)
            selector = action.target_descriptor.selector
            if (
                action.action_id
                in {"click", "type_text", "select_option", "upload_file", "download_file"}
                and selector not in {"document", "window"}
            ):
                expected.selector_present = selector
            return expected

        app_name = str(action.parameters.get("app_name") or action.target_descriptor.selector)
        expected = ExpectedSurface(
            app_name=app_name,
            bundle_id=self._adapters.desktop.bundle_id(app_name),
            allow_modal=False,
        )
        current_title = str(state.get("focused_window_title") or "")
        if action.action_id != "launch_app" and current_title:
            expected.window_title_contains = current_title
        return expected

    def _derive_expected_file_operation(
        self,
        *,
        action: ProposedAction,
    ) -> ExpectedFileOperation | None:
        if action.action_id == "upload_file":
            path = str(action.parameters.get("path") or "")
            normalized = self._adapters.dialog.normalize_path(path)
            return ExpectedFileOperation(
                operation="upload",
                expected_path_prefix=str(normalized.parent),
                expected_filename=normalized.name,
                allowed_roots=self._adapters.dialog.allowed_roots(),
                must_exist=True,
                must_be_writable=False,
                allow_create=False,
            )
        if action.action_id == "download_file":
            output_path = str(action.parameters.get("output_path") or "")
            normalized = (
                self._adapters.dialog.normalize_path(output_path)
                if output_path
                else None
            )
            return ExpectedFileOperation(
                operation="download",
                expected_path_prefix=str(normalized.parent) if normalized is not None else None,
                expected_filename=normalized.name if normalized is not None else None,
                allowed_roots=self._adapters.dialog.allowed_roots(),
                must_exist=False,
                must_be_writable=True,
                allow_create=True,
            )
        return None

    def _observe_file_operation(
        self,
        *,
        action: ProposedAction,
        expected_file_operation: ExpectedFileOperation,
        use_execution_result: bool,
    ) -> FileOperationObservation:
        selected_path: str | None = None
        path_hint: str | None = None
        download_completed: bool | None = None
        if expected_file_operation.operation == "upload":
            selected_path = (
                str(action.execution_result.get("selected_file") or "")
                if use_execution_result
                else str(action.parameters.get("path") or "")
            ) or None
            path_hint = selected_path
        if expected_file_operation.operation == "download":
            path_hint = (
                str(action.execution_result.get("download_path") or "")
                if use_execution_result
                else str(action.parameters.get("output_path") or "")
            ) or None
            download_completed = bool(
                use_execution_result and action.execution_result.get("download_path")
            )
        return self._adapters.dialog.observe_file_operation(
            path=path_hint,
            selected_path=selected_path,
            dialog_open=bool(self._desktop_dialog_open_for(action)),
            download_completed=download_completed,
            allow_create=expected_file_operation.allow_create,
        )

    def _verify_file_operation(
        self,
        *,
        expected_file_operation: ExpectedFileOperation,
        observed_file_operation: FileOperationObservation,
        executed: bool,
    ) -> VerificationResult:
        mismatch = self._compare_file_operation(
            expected_file_operation=expected_file_operation,
            observed_file_operation=observed_file_operation,
            executed=executed,
        )
        verified = mismatch is None
        return VerificationResult(
            verified=verified,
            kind="file_operation",
            summary=(
                "File operation matches policy and filesystem expectations."
                if verified
                else mismatch.message
            ),
            expected=expected_file_operation.model_dump(mode="json"),
            observed=observed_file_operation.model_dump(mode="json"),
            mismatch_code=None if verified else mismatch.code,
            retryable=False,
            expected_file_operation=expected_file_operation,
            observed_file_operation=observed_file_operation,
            file_operation_mismatch=mismatch,
        )

    def _compare_file_operation(
        self,
        *,
        expected_file_operation: ExpectedFileOperation,
        observed_file_operation: FileOperationObservation,
        executed: bool,
    ) -> FileOperationMismatch | None:
        expected = expected_file_operation.model_dump(mode="json")
        observed = observed_file_operation.model_dump(mode="json")
        resolved_path = observed_file_operation.resolved_path or ""
        if observed_file_operation.within_allowed_roots is False:
            return FileOperationMismatch(
                code="path_outside_allowed_roots",
                message=(
                    "Runtime stopped because the file path is outside the allowed roots: "
                    f"{resolved_path or observed_file_operation.selected_path or 'unknown'}."
                ),
                expected=expected,
                observed=observed,
            )
        if (
            expected_file_operation.expected_path_prefix
            and resolved_path
            and not resolved_path.startswith(expected_file_operation.expected_path_prefix)
        ):
            return FileOperationMismatch(
                code="path_outside_allowed_roots",
                message=(
                    "Runtime stopped because the resolved file path drifted away from the "
                    f"expected prefix {expected_file_operation.expected_path_prefix!r}."
                ),
                expected=expected,
                observed=observed,
            )
        if expected_file_operation.expected_filename:
            observed_name = Path(resolved_path).name if resolved_path else ""
            if observed_name and observed_name != expected_file_operation.expected_filename:
                return FileOperationMismatch(
                    code="wrong_filename",
                    message=(
                        "Runtime stopped because the resolved file name "
                        f"{observed_name!r} does not match "
                        f"{expected_file_operation.expected_filename!r}."
                    ),
                    expected=expected,
                    observed=observed,
                )
        if expected_file_operation.must_exist and observed_file_operation.file_exists is False:
            return FileOperationMismatch(
                code="file_missing",
                message="Runtime stopped because the expected source file does not exist.",
                expected=expected,
                observed=observed,
            )
        if (
            expected_file_operation.must_be_writable
            and observed_file_operation.writable is False
        ):
            return FileOperationMismatch(
                code="not_writable",
                message="Runtime stopped because the destination path is not writable.",
                expected=expected,
                observed=observed,
            )
        if (
            executed
            and expected_file_operation.operation == "upload"
            and not observed_file_operation.selected_path
        ):
            return FileOperationMismatch(
                code="selection_missing",
                message="Runtime stopped because the upload dialog did not return a file.",
                expected=expected,
                observed=observed,
            )
        if executed and expected_file_operation.operation == "download":
            if not observed_file_operation.resolved_path:
                return FileOperationMismatch(
                    code="file_not_created",
                    message="Runtime stopped because the download did not produce a file path.",
                    expected=expected,
                    observed=observed,
                )
            if observed_file_operation.file_exists is False:
                return FileOperationMismatch(
                    code="file_not_created",
                    message="Runtime stopped because the download target was not created.",
                    expected=expected,
                    observed=observed,
                )
            if observed_file_operation.download_completed is False:
                return FileOperationMismatch(
                    code="download_incomplete",
                    message="Runtime stopped because the download did not complete in time.",
                    expected=expected,
                    observed=observed,
                )
            if not observed_file_operation.file_size_bytes:
                return FileOperationMismatch(
                    code="download_incomplete",
                    message="Runtime stopped because the downloaded artifact is empty.",
                    expected=expected,
                    observed=observed,
                )
        return None

    def _store_file_operation_state(
        self,
        *,
        state: dict[str, Any],
        expected_file_operation: ExpectedFileOperation | None,
        observed_file_operation: FileOperationObservation | None,
        file_operation_mismatch: FileOperationMismatch | None,
    ) -> None:
        state["expected_file_operation"] = (
            expected_file_operation.model_dump(mode="json")
            if expected_file_operation is not None
            else None
        )
        state["observed_file_operation"] = (
            observed_file_operation.model_dump(mode="json")
            if observed_file_operation is not None
            else None
        )
        state["file_operation_mismatch"] = (
            file_operation_mismatch.model_dump(mode="json")
            if file_operation_mismatch is not None
            else None
        )

    def _merge_verification_results(
        self,
        *,
        primary: VerificationResult,
        secondary: VerificationResult | None,
    ) -> VerificationResult:
        if secondary is None:
            return primary
        failing = primary if not primary.verified else secondary if not secondary.verified else None
        expected = dict(primary.expected)
        observed = dict(primary.observed)
        if secondary.expected:
            expected["file_operation"] = secondary.expected
        if secondary.observed:
            observed["file_operation"] = secondary.observed
        summaries = [item for item in [primary.summary, secondary.summary] if item]
        return VerificationResult(
            verified=primary.verified and secondary.verified,
            kind=primary.kind if primary.kind != "none" else secondary.kind,
            summary=" ".join(summaries),
            expected=expected,
            observed=observed,
            mismatch_code=failing.mismatch_code if failing is not None else None,
            retryable=primary.retryable or secondary.retryable,
            expected_surface=primary.expected_surface or secondary.expected_surface,
            observed_surface=primary.observed_surface or secondary.observed_surface,
            surface_mismatch=primary.surface_mismatch or secondary.surface_mismatch,
            expected_file_operation=(
                primary.expected_file_operation or secondary.expected_file_operation
            ),
            observed_file_operation=(
                primary.observed_file_operation or secondary.observed_file_operation
            ),
            file_operation_mismatch=(
                primary.file_operation_mismatch or secondary.file_operation_mismatch
            ),
        )

    def _desktop_dialog_open_for(self, action: ProposedAction) -> bool:
        if action.app_identity.startswith("browser:"):
            return bool(self._adapters.desktop.detect_dialog("Safari"))
        app_name = str(action.parameters.get("app_name") or action.target_descriptor.selector)
        return bool(self._adapters.desktop.detect_dialog(app_name))

    def _record_file_artifacts(
        self,
        *,
        state: dict[str, Any],
        action: ProposedAction,
        file_verification: VerificationResult | None,
    ) -> None:
        if file_verification is None or not file_verification.verified:
            return
        artifact: dict[str, Any] = {}
        if action.execution_result.get("selected_file"):
            selected = str(action.execution_result["selected_file"])
            artifact["selected_file"] = selected
            if Path(selected).exists():
                artifact["selected_file_size"] = Path(selected).stat().st_size
        if action.execution_result.get("download_path"):
            download_path = str(action.execution_result["download_path"])
            artifact["download_path"] = download_path
            if Path(download_path).exists():
                artifact["size_bytes"] = Path(download_path).stat().st_size
        if artifact:
            state["artifacts"][action.action_id] = artifact

    def _verify_surface(
        self,
        *,
        expected_surface: ExpectedSurface,
        observed_surface: SurfaceObservation,
    ) -> VerificationResult:
        surface_mismatch = self._compare_surface(
            expected_surface=expected_surface,
            observed_surface=observed_surface,
        )
        verified = surface_mismatch is None
        return VerificationResult(
            verified=verified,
            kind="expected_surface",
            summary=(
                "Observed surface matches the runtime preconditions."
                if verified
                else surface_mismatch.message
            ),
            expected=expected_surface.model_dump(mode="json"),
            observed=observed_surface.model_dump(mode="json"),
            mismatch_code=None if verified else surface_mismatch.code,
            retryable=False,
            expected_surface=expected_surface,
            observed_surface=observed_surface,
            surface_mismatch=surface_mismatch,
        )

    def _compare_surface(
        self,
        *,
        expected_surface: ExpectedSurface,
        observed_surface: SurfaceObservation,
    ) -> SurfaceMismatch | None:
        expected = expected_surface.model_dump(mode="json")
        observed = observed_surface.model_dump(mode="json")
        if (
            expected_surface.app_name
            and observed_surface.foreground_app != expected_surface.app_name
        ):
            return SurfaceMismatch(
                code="wrong_app",
                message=(
                    "Runtime stopped before execution because the foreground app drifted "
                    f"from {expected_surface.app_name} to "
                    f"{observed_surface.foreground_app or 'unknown'}."
                ),
                expected=expected,
                observed=observed,
            )
        if (
            expected_surface.bundle_id
            and observed_surface.bundle_id
            and observed_surface.bundle_id != expected_surface.bundle_id
        ):
            return SurfaceMismatch(
                code="wrong_app",
                message=(
                    "Runtime stopped before execution because the foreground app bundle id "
                    f"drifted from {expected_surface.bundle_id} to {observed_surface.bundle_id}."
                ),
                expected=expected,
                observed=observed,
            )
        if expected_surface.window_title_contains:
            observed_title = (
                observed_surface.focused_window_title or observed_surface.active_tab_title or ""
            )
            if expected_surface.window_title_contains not in observed_title:
                return SurfaceMismatch(
                    code="wrong_window",
                    message=(
                        "Runtime stopped before execution because the focused window no longer "
                        f"matches {expected_surface.window_title_contains!r}."
                    ),
                    expected=expected,
                    observed=observed,
                )
        if expected_surface.tab_url_host or expected_surface.tab_url_prefix:
            active_tab_url = observed_surface.active_tab_url or ""
            parsed = urlparse(active_tab_url)
            host_matches = (
                not expected_surface.tab_url_host
                or parsed.netloc == expected_surface.tab_url_host
            )
            prefix_matches = (
                not expected_surface.tab_url_prefix
                or active_tab_url.startswith(expected_surface.tab_url_prefix)
            )
            if not host_matches or not prefix_matches:
                return SurfaceMismatch(
                    code="wrong_tab",
                    message=(
                        "Runtime stopped before execution because the active tab drifted to "
                        f"{active_tab_url or 'an unknown tab'}."
                    ),
                    expected=expected,
                    observed=observed,
                )
        if not expected_surface.allow_modal and observed_surface.modal_detected:
            return SurfaceMismatch(
                code="unexpected_modal",
                message="Runtime stopped before execution because an unexpected modal is visible.",
                expected=expected,
                observed=observed,
            )
        if expected_surface.selector_present:
            visible_selectors = set(observed_surface.visible_selectors or [])
            if expected_surface.selector_present not in visible_selectors:
                return SurfaceMismatch(
                    code="missing_expected_selector",
                    message=(
                        "Runtime stopped before execution because the expected selector "
                        f"{expected_surface.selector_present!r} is no longer visible."
                    ),
                    expected=expected,
                    observed=observed,
                )
        return None

    def _store_surface_state(
        self,
        *,
        state: dict[str, Any],
        expected_surface: ExpectedSurface,
        observed_surface: SurfaceObservation,
        surface_mismatch: SurfaceMismatch | None,
    ) -> None:
        state["expected_surface"] = expected_surface.model_dump(mode="json")
        state["observed_surface"] = observed_surface.model_dump(mode="json")
        state["surface_mismatch"] = (
            surface_mismatch.model_dump(mode="json") if surface_mismatch is not None else None
        )
        state["foreground_app"] = observed_surface.foreground_app
        state["focused_window_title"] = observed_surface.focused_window_title
        state["active_window"] = observed_surface.focused_window_title or state.get("active_window")
        state["browser_tab_title"] = observed_surface.active_tab_title or state.get(
            "browser_tab_title"
        )
        state["current_url"] = observed_surface.active_tab_url or state.get("current_url")
        state["active_surface"] = _surface_label(observed_surface)

    def _apply_execution_result(
        self,
        *,
        state: dict[str, Any],
        action: ProposedAction,
    ) -> None:
        if action.execution_result.get("url"):
            state["current_url"] = str(action.execution_result["url"])
        if action.execution_result.get("title"):
            state["browser_tab_title"] = str(action.execution_result["title"])
        if action.execution_result.get("app_name"):
            state["foreground_app"] = str(action.execution_result["app_name"])

    def _inspect_action(self, action: ProposedAction) -> PerceptionSnapshot:
        if action.app_identity.startswith("browser:"):
            return self._select_adapter(action).inspect_target(target=action.target_descriptor)
        return self._inspect_desktop_action(action)

    def _execute_action(self, action: ProposedAction) -> dict[str, Any]:
        if action.app_identity.startswith("browser:"):
            return self._select_adapter(action).execute(action=action)
        app_name = str(action.parameters.get("app_name") or action.target_descriptor.selector)
        if action.action_id == "launch_app":
            self._adapters.desktop.launch_app(app_name)
            self._adapters.desktop.focus_window(app_name)
            return {"status": "executed", "app_name": app_name}
        if action.action_id == "focus_window":
            self._adapters.desktop.focus_window(app_name)
            return {"status": "executed", "app_name": app_name}
        raise RuntimeError(f"unsupported desktop action: {action.action_id}")

    def _verify_action(
        self,
        *,
        action: ProposedAction,
        before: PerceptionSnapshot | None = None,
    ) -> VerificationResult:
        if action.app_identity.startswith("browser:"):
            return self._select_adapter(action).verify(action=action, before=before)
        frontmost = self._adapters.desktop.frontmost_app()
        expected = str(action.parameters.get("app_name") or action.target_descriptor.selector)
        verified = frontmost == expected
        return VerificationResult(
            verified=verified,
            kind="frontmost_app",
            summary=(
                "Foreground application matches the requested window."
                if verified
                else "Foreground application does not match the requested window."
            ),
            expected={"frontmost_app": expected},
            observed={"frontmost_app": frontmost},
            mismatch_code=None if verified else "frontmost_app_mismatch",
            retryable=not verified,
        )

    def _inspect_desktop_action(self, action: ProposedAction) -> PerceptionSnapshot:
        app_name = str(action.parameters.get("app_name") or action.target_descriptor.selector)
        windows = self._adapters.desktop.inspect_windows(app_name)
        focused = self._adapters.desktop.frontmost_app() == app_name
        window_title = windows[0].window_title if windows else app_name
        dialog_open = windows[0].dialog_open if windows else False
        selector_context = SelectorContext(
            selector=app_name,
            selector_source="desktop",
            selector_trace=[app_name],
        )
        fingerprint = build_perception_fingerprint(
            window_or_tab_identity=f"desktop:{app_name}:{window_title}",
            app_identity=f"desktop:{app_name}",
            selector_context=selector_context.model_dump(mode="json"),
            screenshot_hash=hashlib.sha256(
                f"{app_name}|{window_title}|{focused}".encode()
            ).hexdigest(),
        )
        return PerceptionSnapshot(
            source=PerceptionSource.DETERMINISTIC_SELECTOR,
            confidence=0.97 if windows or focused else 0.52,
            perception_fingerprint=fingerprint,
            sensitive_surface=False,
            focused=focused,
            unexpected_modal=dialog_open,
            selector_ambiguous=False,
            window_or_tab_identity=f"desktop:{app_name}:{window_title}",
            app_identity=f"desktop:{app_name}",
            current_url="desktop://front",
            selector_context=selector_context,
            evidence=EvidenceEnvelope(
                screenshot_hash=fingerprint,
                redacted_fingerprint=fingerprint,
                accessibility_subset={
                    "window_title": window_title,
                    "dialog_open": dialog_open,
                },
            ),
        )

    def _requires_approval(
        self,
        *,
        request: SessionRequest,
        action: ProposedAction,
    ) -> bool:
        if request.mode == ComputerUseMode.STEP_APPROVAL:
            return True
        return action.risk_class in {RiskClass.HIGH, RiskClass.CRITICAL}

    def _request_approval(
        self,
        *,
        request: SessionRequest,
        action: ProposedAction,
        perception,
        policy: BrowserAllowlistPolicy,
        recorder: EventRecorder,
        job: JobRun,
        state: dict[str, Any],
        paths: TeamArtifactPaths,
        events: list[TeamEvent],
        actions: list[ProposedAction],
    ) -> str:
        snapshot = approval_snapshot_payload(
            action=action,
            perception=perception,
            policy_hash=policy.policy_hash(),
        )
        decision, ticket = self._governance.request_device_action_approval(
            run_id=request.run_id,
            target_ref=action.target_descriptor.target_ref,
            action_payload=snapshot,
            explain="computer-use action requires approval before execution",
        )
        approval_id = ticket.approval_id if ticket is not None else ""
        self._set_execution_state(state, SessionExecutionState.AWAITING_APPROVAL)
        state["pending_approval_id"] = approval_id
        state["stage"] = ExecutionStage.REQUIRE_APPROVAL.value
        job.status = JobStatus.BLOCKED
        recorder.emit(
            "approval_requested",
            phase="approval",
            status_before=JobStatus.RUNNING.value,
            status_after=JobStatus.BLOCKED.value,
            approval_id=approval_id or None,
            data={
                "approval_id": approval_id,
                "status": "pending",
                "target": "device_action",
                "reason_code": decision.reason_code,
            },
        )
        recorder.emit(
            "approval_required",
            phase="computer_use",
            status_before=JobStatus.RUNNING.value,
            status_after=JobStatus.BLOCKED.value,
            approval_id=approval_id or None,
            data={"approval_id": approval_id, "action_id": action.action_id},
        )
        self._write_runtime_status(
            paths=paths,
            job=job,
            state=state,
            events=events,
            actions=actions,
        )
        self._registry.update(
            job_id=job.job_id,
            state=SessionExecutionState.AWAITING_APPROVAL.value,
        )
        return approval_id

    def _wait_until_resumed(
        self,
        *,
        control: SessionControlBus,
        ticket_id: str,
        job: JobRun,
        state: dict[str, Any],
        recorder: EventRecorder,
        paths: TeamArtifactPaths,
        events: list[TeamEvent],
        actions: list[ProposedAction],
    ) -> None:
        job.status = JobStatus.BLOCKED
        state["last_safe_checkpoint"] = "approval_wait"
        state["stage"] = ExecutionStage.REQUIRE_APPROVAL.value
        recorder.emit(
            "session_paused",
            phase="computer_use",
            status_before=JobStatus.RUNNING.value,
            status_after=JobStatus.BLOCKED.value,
            approval_id=ticket_id or None,
            data={"reason": "approval_required"},
        )
        self._registry.update(
            job_id=job.job_id,
            state=SessionExecutionState.AWAITING_APPROVAL.value,
        )
        self._write_runtime_status(
            paths=paths,
            job=job,
            state=state,
            events=events,
            actions=actions,
        )
        while True:
            control_state = control.read()
            pending = control_state.pending_command
            if pending is None:
                time.sleep(0.25)
                continue
            self._set_pending_control(state=state, command=pending)
            command = SessionCommand(pending.command_type)
            if command == SessionCommand.PAUSE:
                result = self._build_control_result(
                    command=pending,
                    outcome="rejected",
                    previous_state=SessionExecutionState.AWAITING_APPROVAL,
                    resulting_state=SessionExecutionState.AWAITING_APPROVAL,
                    reason="pause_not_allowed_while_awaiting_approval",
                )
                control.mark_processed(result)
                self._set_last_control_result(state=state, result=result)
                recorder.emit(
                    "computer_use.control_command_rejected",
                    phase="computer_use",
                    status_before=job.status.value,
                    status_after=job.status.value,
                    approval_id=ticket_id or None,
                    data={
                        "command": pending.model_dump(mode="json"),
                        "checkpoint": "approval_wait",
                        "result": result.model_dump(mode="json"),
                    },
                )
                self._write_runtime_status(
                    paths=paths,
                    job=job,
                    state=state,
                    events=events,
                    actions=actions,
                )
                time.sleep(0.1)
                continue
            if command == SessionCommand.STOP:
                recorder.emit(
                    "computer_use.stop_requested",
                    phase="computer_use",
                    status_before=job.status.value,
                    status_after=job.status.value,
                    approval_id=ticket_id or None,
                    data={
                        "command": pending.model_dump(mode="json"),
                        "checkpoint": "approval_wait",
                    },
                )
                self._stop(
                    job=job,
                    state=state,
                    recorder=recorder,
                    paths=paths,
                    events=events,
                    actions=actions,
                    reason="operator_stop",
                    control=control,
                    control_command=pending,
                )
                raise RuntimeError("session stopped by operator")
            if command == SessionCommand.RESUME:
                ticket = self._governance.approval_store.get(ticket_id)
                if ticket is not None and ticket.execution_status.value == "executed":
                    previous_state = self._execution_state(state)
                    recorder.emit(
                        "computer_use.resume_requested",
                        phase="computer_use",
                        status_before=job.status.value,
                        status_after=job.status.value,
                        approval_id=ticket_id or None,
                        data={
                            "command": pending.model_dump(mode="json"),
                            "checkpoint": "approval_wait",
                        },
                    )
                    self._set_execution_state(state, SessionExecutionState.RESUMING)
                    result = self._build_control_result(
                        command=pending,
                        outcome="applied",
                        previous_state=previous_state,
                        resulting_state=SessionExecutionState.RUNNING,
                        reason="approval_resume",
                    )
                    control.mark_processed(result)
                    job.status = JobStatus.RUNNING
                    self._set_execution_state(state, SessionExecutionState.RUNNING)
                    state["pending_approval_id"] = None
                    self._set_last_control_result(state=state, result=result)
                    recorder.emit(
                        "computer_use.resumed",
                        phase="computer_use",
                        status_before=JobStatus.BLOCKED.value,
                        status_after=JobStatus.RUNNING.value,
                        approval_id=ticket_id or None,
                        data={
                            "command": pending.model_dump(mode="json"),
                            "result": result.model_dump(mode="json"),
                        },
                    )
                    recorder.emit(
                        "session_resumed",
                        phase="computer_use",
                        status_before=JobStatus.BLOCKED.value,
                        status_after=JobStatus.RUNNING.value,
                        approval_id=ticket_id or None,
                        data={"reason": "operator_resume"},
                    )
                    self._registry.update(
                        job_id=job.job_id,
                        state=SessionExecutionState.RUNNING.value,
                    )
                    self._write_runtime_status(
                        paths=paths,
                        job=job,
                        state=state,
                        events=events,
                        actions=actions,
                    )
                    return
                result = self._build_control_result(
                    command=pending,
                    outcome="rejected",
                    previous_state=SessionExecutionState.AWAITING_APPROVAL,
                    resulting_state=SessionExecutionState.AWAITING_APPROVAL,
                    reason="approval_not_executed",
                )
                control.mark_processed(result)
                self._set_last_control_result(state=state, result=result)
                recorder.emit(
                    "computer_use.control_command_rejected",
                    phase="computer_use",
                    status_before=job.status.value,
                    status_after=job.status.value,
                    approval_id=ticket_id or None,
                    data={
                        "command": pending.model_dump(mode="json"),
                        "checkpoint": "approval_wait",
                        "result": result.model_dump(mode="json"),
                    },
                )
                self._write_runtime_status(
                    paths=paths,
                    job=job,
                    state=state,
                    events=events,
                    actions=actions,
                )
            time.sleep(0.25)

    def _cooperative_check(
        self,
        *,
        job: JobRun,
        state: dict[str, Any],
        recorder: EventRecorder,
        control: SessionControlBus,
        paths: TeamArtifactPaths,
        events: list[TeamEvent],
        actions: list[ProposedAction],
        checkpoint: str,
    ) -> None:
        state["last_safe_checkpoint"] = checkpoint
        control_state = control.read()
        pending = control_state.pending_command
        if pending is None:
            return
        self._set_pending_control(state=state, command=pending)
        command = SessionCommand(pending.command_type)
        current_state = self._execution_state(state)
        if command == SessionCommand.STOP:
            recorder.emit(
                "computer_use.stop_requested",
                phase="computer_use",
                status_before=job.status.value,
                status_after=job.status.value,
                data={
                    "command": pending.model_dump(mode="json"),
                    "checkpoint": checkpoint,
                },
            )
            self._stop(
                job=job,
                state=state,
                recorder=recorder,
                paths=paths,
                events=events,
                actions=actions,
                reason="operator_stop",
                control=control,
                control_command=pending,
            )
            raise RuntimeError("session stopped by operator")
        if command == SessionCommand.PAUSE:
            if current_state != SessionExecutionState.RUNNING:
                outcome = (
                    "already_applied"
                    if current_state == SessionExecutionState.PAUSED
                    else "rejected"
                )
                result = self._build_control_result(
                    command=pending,
                    outcome=outcome,
                    previous_state=current_state,
                    resulting_state=current_state,
                    reason=(
                        "pause_already_applied"
                        if outcome == "already_applied"
                        else f"pause_not_allowed_from_{current_state.value}"
                    ),
                )
                control.mark_processed(result)
                self._set_last_control_result(state=state, result=result)
                if outcome == "rejected":
                    recorder.emit(
                        "computer_use.control_command_rejected",
                        phase="computer_use",
                        status_before=job.status.value,
                        status_after=job.status.value,
                        data={
                            "command": pending.model_dump(mode="json"),
                            "checkpoint": checkpoint,
                            "result": result.model_dump(mode="json"),
                        },
                    )
                self._write_runtime_status(
                    paths=paths,
                    job=job,
                    state=state,
                    events=events,
                    actions=actions,
                )
                return
            recorder.emit(
                "computer_use.pause_requested",
                phase="computer_use",
                status_before=job.status.value,
                status_after=JobStatus.BLOCKED.value,
                data={
                    "command": pending.model_dump(mode="json"),
                    "checkpoint": checkpoint,
                },
            )
            self._set_execution_state(state, SessionExecutionState.PAUSING)
            job.status = JobStatus.BLOCKED
            state["stage"] = ExecutionStage.CHECKPOINT.value
            result = self._build_control_result(
                command=pending,
                outcome="applied",
                previous_state=current_state,
                resulting_state=SessionExecutionState.PAUSED,
                reason=f"paused_at_{checkpoint}",
            )
            control.mark_processed(result)
            self._set_execution_state(state, SessionExecutionState.PAUSED)
            self._set_last_control_result(state=state, result=result)
            recorder.emit(
                "computer_use.paused",
                phase="computer_use",
                status_before=JobStatus.RUNNING.value,
                status_after=JobStatus.BLOCKED.value,
                data={
                    "command": pending.model_dump(mode="json"),
                    "checkpoint": checkpoint,
                    "result": result.model_dump(mode="json"),
                },
            )
            recorder.emit(
                "session_paused",
                phase="computer_use",
                status_before=JobStatus.RUNNING.value,
                status_after=JobStatus.BLOCKED.value,
                data={"reason": "operator_pause"},
            )
            self._registry.update(job_id=job.job_id, state=SessionExecutionState.PAUSED.value)
            self._write_runtime_status(
                paths=paths,
                job=job,
                state=state,
                events=events,
                actions=actions,
            )
            while True:
                control_state = control.read()
                pending = control_state.pending_command
                if pending is None:
                    time.sleep(0.25)
                    continue
                self._set_pending_control(state=state, command=pending)
                command = SessionCommand(pending.command_type)
                if command == SessionCommand.STOP:
                    recorder.emit(
                        "computer_use.stop_requested",
                        phase="computer_use",
                        status_before=job.status.value,
                        status_after=job.status.value,
                        data={
                            "command": pending.model_dump(mode="json"),
                            "checkpoint": "paused_wait",
                        },
                    )
                    self._stop(
                        job=job,
                        state=state,
                        recorder=recorder,
                        paths=paths,
                        events=events,
                        actions=actions,
                        reason="operator_stop",
                        control=control,
                        control_command=pending,
                    )
                    raise RuntimeError("session stopped by operator")
                if command == SessionCommand.PAUSE:
                    result = self._build_control_result(
                        command=pending,
                        outcome="already_applied",
                        previous_state=SessionExecutionState.PAUSED,
                        resulting_state=SessionExecutionState.PAUSED,
                        reason="pause_already_applied",
                    )
                    control.mark_processed(result)
                    self._set_last_control_result(state=state, result=result)
                    self._write_runtime_status(
                        paths=paths,
                        job=job,
                        state=state,
                        events=events,
                        actions=actions,
                    )
                    time.sleep(0.1)
                    continue
                if command == SessionCommand.RESUME:
                    recorder.emit(
                        "computer_use.resume_requested",
                        phase="computer_use",
                        status_before=JobStatus.BLOCKED.value,
                        status_after=JobStatus.RUNNING.value,
                        data={
                            "command": pending.model_dump(mode="json"),
                            "checkpoint": "paused_wait",
                        },
                    )
                    self._set_execution_state(state, SessionExecutionState.RESUMING)
                    result = self._build_control_result(
                        command=pending,
                        outcome="applied",
                        previous_state=SessionExecutionState.PAUSED,
                        resulting_state=SessionExecutionState.RUNNING,
                        reason="operator_resume",
                    )
                    control.mark_processed(result)
                    job.status = JobStatus.RUNNING
                    self._set_execution_state(state, SessionExecutionState.RUNNING)
                    self._set_last_control_result(state=state, result=result)
                    recorder.emit(
                        "computer_use.resumed",
                        phase="computer_use",
                        status_before=JobStatus.BLOCKED.value,
                        status_after=JobStatus.RUNNING.value,
                        data={
                            "command": pending.model_dump(mode="json"),
                            "result": result.model_dump(mode="json"),
                        },
                    )
                    recorder.emit(
                        "session_resumed",
                        phase="computer_use",
                        status_before=JobStatus.BLOCKED.value,
                        status_after=JobStatus.RUNNING.value,
                        data={"reason": "operator_resume"},
                    )
                    self._registry.update(
                        job_id=job.job_id,
                        state=SessionExecutionState.RUNNING.value,
                    )
                    self._write_runtime_status(
                        paths=paths,
                        job=job,
                        state=state,
                        events=events,
                        actions=actions,
                    )
                    return
                result = self._build_control_result(
                    command=pending,
                    outcome="rejected",
                    previous_state=SessionExecutionState.PAUSED,
                    resulting_state=SessionExecutionState.PAUSED,
                    reason=f"{command.value}_not_allowed_from_paused",
                )
                control.mark_processed(result)
                self._set_last_control_result(state=state, result=result)
                recorder.emit(
                    "computer_use.control_command_rejected",
                    phase="computer_use",
                    status_before=job.status.value,
                    status_after=job.status.value,
                    data={
                        "command": pending.model_dump(mode="json"),
                        "checkpoint": "paused_wait",
                        "result": result.model_dump(mode="json"),
                    },
                )
                self._write_runtime_status(
                    paths=paths,
                    job=job,
                    state=state,
                    events=events,
                    actions=actions,
                )
                time.sleep(0.25)
        if command == SessionCommand.RESUME:
            result = self._build_control_result(
                command=pending,
                outcome="rejected",
                previous_state=current_state,
                resulting_state=current_state,
                reason=f"resume_not_allowed_from_{current_state.value}",
            )
            control.mark_processed(result)
            self._set_last_control_result(state=state, result=result)
            recorder.emit(
                "computer_use.control_command_rejected",
                phase="computer_use",
                status_before=job.status.value,
                status_after=job.status.value,
                data={
                    "command": pending.model_dump(mode="json"),
                    "checkpoint": checkpoint,
                    "result": result.model_dump(mode="json"),
                },
            )
            self._write_runtime_status(
                paths=paths,
                job=job,
                state=state,
                events=events,
                actions=actions,
            )

    def _surface_fail_closed(
        self,
        *,
        action: ProposedAction,
        verification: VerificationResult,
        job: JobRun,
        state: dict[str, Any],
        recorder: EventRecorder,
        paths: TeamArtifactPaths,
        events: list[TeamEvent],
        actions: list[ProposedAction],
    ) -> None:
        if (
            verification.expected_surface is not None
            and verification.observed_surface is not None
        ):
            self._store_surface_state(
                state=state,
                expected_surface=verification.expected_surface,
                observed_surface=verification.observed_surface,
                surface_mismatch=verification.surface_mismatch,
            )
        job.status = JobStatus.FAILED
        job.finished_at = datetime.now(UTC)
        reason = verification.mismatch_code or "surface_mismatch"
        job.final_output = f"computer-use surface mismatch: {reason}"
        self._set_execution_state(state, SessionExecutionState.FAILED)
        state["stage"] = ExecutionStage.STOPPED.value
        state["last_error"] = reason
        state["last_verification_result"] = verification.model_dump(mode="json")
        recorder.emit(
            "computer_use.surface_mismatch",
            phase="computer_use",
            status_before=JobStatus.RUNNING.value,
            status_after=JobStatus.FAILED.value,
            data={
                **_action_payload(action),
                "reason_code": reason,
                "reason_message": verification.summary,
                "expected_surface": (
                    verification.expected_surface.model_dump(mode="json")
                    if verification.expected_surface is not None
                    else {}
                ),
                "observed_surface": (
                    verification.observed_surface.model_dump(mode="json")
                    if verification.observed_surface is not None
                    else {}
                ),
                "verification": verification.model_dump(mode="json"),
            },
        )
        recorder.emit(
            "action_failed",
            phase="computer_use",
            status_before=JobStatus.RUNNING.value,
            status_after=JobStatus.FAILED.value,
            data={
                **_action_payload(action),
                "reason_code": reason,
                "verification": verification.model_dump(mode="json"),
            },
        )
        recorder.emit(
            "session_stopped",
            phase="computer_use",
            status_before=JobStatus.RUNNING.value,
            status_after=JobStatus.FAILED.value,
            data={"reason": reason},
        )
        self._write_runtime_status(
            paths=paths,
            job=job,
            state=state,
            events=events,
            actions=actions,
        )

    def _file_operation_fail_closed(
        self,
        *,
        action: ProposedAction,
        verification: VerificationResult,
        job: JobRun,
        state: dict[str, Any],
        recorder: EventRecorder,
        paths: TeamArtifactPaths,
        events: list[TeamEvent],
        actions: list[ProposedAction],
    ) -> None:
        if (
            verification.expected_file_operation is not None
            and verification.observed_file_operation is not None
        ):
            self._store_file_operation_state(
                state=state,
                expected_file_operation=verification.expected_file_operation,
                observed_file_operation=verification.observed_file_operation,
                file_operation_mismatch=verification.file_operation_mismatch,
            )
        job.status = JobStatus.FAILED
        job.finished_at = datetime.now(UTC)
        reason = verification.mismatch_code or "file_operation_mismatch"
        job.final_output = f"computer-use file operation mismatch: {reason}"
        self._set_execution_state(state, SessionExecutionState.FAILED)
        state["stage"] = ExecutionStage.STOPPED.value
        state["last_error"] = reason
        state["last_verification_result"] = verification.model_dump(mode="json")
        recorder.emit(
            "computer_use.file_operation_mismatch",
            phase="computer_use",
            status_before=JobStatus.RUNNING.value,
            status_after=JobStatus.FAILED.value,
            data={
                **_action_payload(action),
                "reason_code": reason,
                "reason_message": verification.summary,
                "expected_file_operation": (
                    verification.expected_file_operation.model_dump(mode="json")
                    if verification.expected_file_operation is not None
                    else {}
                ),
                "observed_file_operation": (
                    verification.observed_file_operation.model_dump(mode="json")
                    if verification.observed_file_operation is not None
                    else {}
                ),
                "verification": verification.model_dump(mode="json"),
                "artifact_path": (
                    str(action.execution_result.get("download_path") or "")
                    or str(action.execution_result.get("selected_file") or "")
                    or None
                ),
            },
        )
        recorder.emit(
            "action_failed",
            phase="computer_use",
            status_before=JobStatus.RUNNING.value,
            status_after=JobStatus.FAILED.value,
            data={
                **_action_payload(action),
                "reason_code": reason,
                "verification": verification.model_dump(mode="json"),
            },
        )
        recorder.emit(
            "session_stopped",
            phase="computer_use",
            status_before=JobStatus.RUNNING.value,
            status_after=JobStatus.FAILED.value,
            data={"reason": reason},
        )
        self._write_runtime_status(
            paths=paths,
            job=job,
            state=state,
            events=events,
            actions=actions,
        )

    def _hard_stop(
        self,
        *,
        stop_reason: ComputerUseStopReason,
        action: ProposedAction,
        job: JobRun,
        state: dict[str, Any],
        recorder: EventRecorder,
        paths: TeamArtifactPaths,
        events: list[TeamEvent],
        actions: list[ProposedAction],
        policy: BrowserAllowlistPolicy,
        perception,
    ) -> None:
        del policy, perception
        job.status = JobStatus.FAILED
        job.finished_at = datetime.now(UTC)
        job.final_output = f"computer-use hard stop: {stop_reason.value}"
        self._set_execution_state(state, SessionExecutionState.FAILED)
        state["stage"] = ExecutionStage.STOPPED.value
        state["last_error"] = stop_reason.value
        recorder.emit(
            "action_failed",
            phase="computer_use",
            status_before=JobStatus.RUNNING.value,
            status_after=JobStatus.FAILED.value,
            data={"action_id": action.action_id, "reason_code": stop_reason.value},
        )
        recorder.emit(
            "session_stopped",
            phase="computer_use",
            status_before=JobStatus.RUNNING.value,
            status_after=JobStatus.FAILED.value,
            data={"reason": stop_reason.value},
        )
        self._write_runtime_status(
            paths=paths,
            job=job,
            state=state,
            events=events,
            actions=actions,
        )

    def _stop(
        self,
        *,
        job: JobRun,
        state: dict[str, Any],
        recorder: EventRecorder,
        paths: TeamArtifactPaths,
        events: list[TeamEvent],
        actions: list[ProposedAction],
        reason: str,
        control: SessionControlBus | None = None,
        control_command: ControlCommand | None = None,
    ) -> None:
        job.status = JobStatus.FAILED
        job.finished_at = datetime.now(UTC)
        job.final_output = "computer-use session stopped"
        previous_state = self._execution_state(state)
        if previous_state not in {SessionExecutionState.STOPPING, SessionExecutionState.STOPPED}:
            self._set_execution_state(state, SessionExecutionState.STOPPING)
        self._set_execution_state(state, SessionExecutionState.STOPPED)
        state["stage"] = ExecutionStage.STOPPED.value
        state["last_error"] = reason
        state["stopped_by_user"] = True
        if control is not None and control_command is not None:
            result = self._build_control_result(
                command=control_command,
                outcome="applied",
                previous_state=previous_state,
                resulting_state=SessionExecutionState.STOPPED,
                reason=reason,
            )
            control.mark_processed(result)
            self._set_last_control_result(state=state, result=result)
            recorder.emit(
                "computer_use.stopped",
                phase="computer_use",
                status_before=JobStatus.RUNNING.value,
                status_after=JobStatus.FAILED.value,
                data={
                    "command": control_command.model_dump(mode="json"),
                    "result": result.model_dump(mode="json"),
                },
            )
        recorder.emit(
            "session_stopped",
            phase="computer_use",
            status_before=JobStatus.RUNNING.value,
            status_after=JobStatus.FAILED.value,
            data={"reason": reason},
        )
        self._registry.update(job_id=job.job_id, state=SessionExecutionState.STOPPED.value)
        self._write_runtime_status(
            paths=paths,
            job=job,
            state=state,
            events=events,
            actions=actions,
        )

    def _write_runtime_status(
        self,
        *,
        paths: TeamArtifactPaths,
        job: JobRun,
        state: dict[str, Any],
        events: list[TeamEvent],
        actions: list[ProposedAction],
        policy: BrowserAllowlistPolicy | None = None,
        perception=None,
    ) -> None:
        write_status(
            paths,
            {
                "job": job.model_dump(mode="json"),
                "tasks": [],
                "audit_envelope_path": str(paths.envelope_path),
                "job_dir": str(paths.job_dir),
                "resume_outcomes": [],
                "continuation": {},
                "computer_use": {
                    **state,
                    "world_model": self._world_model(
                        job=job,
                        state=state,
                        actions=actions,
                        policy=policy,
                        perception=perception,
                    ),
                    "recorder": (
                        build_recorder_artifact(
                            mode=ComputerUseMode(state["mode"]),
                            perception=perception,
                            actions=actions,
                            approval_ids=[
                                str(state.get("pending_approval_id") or "")
                            ]
                            if perception is not None and state.get("pending_approval_id")
                            else [],
                            raw_evidence_allowed=False,
                        )
                        if perception is not None
                        else {"mode": state["mode"], "traces": []}
                    ),
                    "event_count": len(events),
                },
            },
        )

    def _world_model(
        self,
        *,
        job: JobRun,
        state: dict[str, Any],
        actions: list[ProposedAction],
        policy: BrowserAllowlistPolicy | None,
        perception,
    ) -> dict[str, Any]:
        expected_surface_payload = dict(state.get("expected_surface") or {})
        observed_surface_payload = dict(state.get("observed_surface") or {})
        surface_mismatch_payload = dict(state.get("surface_mismatch") or {})
        expected_file_operation_payload = dict(state.get("expected_file_operation") or {})
        observed_file_operation_payload = dict(state.get("observed_file_operation") or {})
        file_operation_mismatch_payload = dict(state.get("file_operation_mismatch") or {})
        pending_control_payload = dict(state.get("pending_command") or {})
        last_control_result_payload = dict(state.get("last_control_result") or {})
        title_from_perception = (
            str((perception.evidence.accessibility_subset or {}).get("title") or "")
            if perception is not None
            else ""
        )
        model = WorldModel(
            active_run_id=job.job_id,
            objective=job.request,
            stage=ExecutionStage(str(state.get("stage") or ExecutionStage.PLAN.value)),
            last_known_status=job.status.value,
            active_window=(
                WindowState(
                    window_identity=str(state.get("active_window") or ""),
                    app_identity=str(state.get("active_app") or ""),
                    focused=self._execution_state(state) not in {
                        SessionExecutionState.PAUSED,
                        SessionExecutionState.STOPPED,
                    },
                )
                if state.get("active_window") and state.get("active_app")
                else None
            ),
            open_windows=[],
            execution_state=self._execution_state(state),
            active_application_identity=(
                str(state.get("foreground_app") or state.get("active_app") or "") or None
            ),
            active_surface=str(state.get("active_surface") or "") or None,
            focused_window_title=str(state.get("focused_window_title") or "") or None,
            current_url=str(state.get("current_url") or "") or None,
            browser_tab_title=str(state.get("browser_tab_title") or title_from_perception or "")
            or None,
            expected_surface=(
                ExpectedSurface.model_validate(expected_surface_payload)
                if expected_surface_payload
                else None
            ),
            observed_surface=(
                SurfaceObservation.model_validate(observed_surface_payload)
                if observed_surface_payload
                else None
            ),
            surface_mismatch=(
                SurfaceMismatch.model_validate(surface_mismatch_payload)
                if surface_mismatch_payload
                else None
            ),
            expected_file_operation=(
                ExpectedFileOperation.model_validate(expected_file_operation_payload)
                if expected_file_operation_payload
                else None
            ),
            observed_file_operation=(
                FileOperationObservation.model_validate(observed_file_operation_payload)
                if observed_file_operation_payload
                else None
            ),
            file_operation_mismatch=(
                FileOperationMismatch.model_validate(file_operation_mismatch_payload)
                if file_operation_mismatch_payload
                else None
            ),
            observed_targets=[item.target_descriptor for item in actions],
            visible_target_set=[item.target_descriptor.selector for item in actions],
            changed_resources=[],
            pending_approval_ids=(
                [str(state.get("pending_approval_id"))]
                if state.get("pending_approval_id")
                else []
            ),
            pending_dialog_state={
                "dialog_open": bool(observed_file_operation_payload.get("dialog_open"))
                or bool(observed_surface_payload.get("modal_detected"))
            },
            selected_file_state={
                "selected_path": observed_file_operation_payload.get("selected_path"),
                "resolved_path": observed_file_operation_payload.get("resolved_path"),
            }
            if observed_file_operation_payload
            else (
                {"download_dir": str(self._adapters.dialog._allowed_roots[0])}
                if hasattr(self._adapters.dialog, "_allowed_roots")
                else {}
            ),
            filesystem_result_set=[
                str(item.get("download_path") or "")
                for item in state.get("artifacts", {}).values()
                if item.get("download_path")
            ]
            + (
                [str(observed_file_operation_payload.get("resolved_path"))]
                if observed_file_operation_payload.get("resolved_path")
                and expected_file_operation_payload.get("operation") == "download"
                else []
            ),
            last_completed_action=str(state.get("active_action") or "") or None,
            last_verified_effect=str(state.get("last_verified_effect") or "") or None,
            last_verification_result=dict(state.get("last_verification_result") or {}),
            last_safe_checkpoint=str(state.get("last_safe_checkpoint") or "") or None,
            pending_control=(
                ControlCommand.model_validate(pending_control_payload)
                if pending_control_payload
                else None
            ),
            resume_allowed=bool(state.get("resume_allowed")),
            last_control_result=(
                ControlCommandResult.model_validate(last_control_result_payload)
                if last_control_result_payload
                else None
            ),
            drift_detected=bool(
                surface_mismatch_payload
                or state.get("last_error")
                in {
                    ComputerUseStopReason.FOCUS_DRIFT.value,
                    ComputerUseStopReason.UNEXPECTED_MODAL.value,
                }
            ),
            user_intervention_required=bool(
                state.get("pending_approval_id")
                or self._execution_state(state)
                in {
                    SessionExecutionState.PAUSED,
                    SessionExecutionState.PAUSING,
                    SessionExecutionState.STOPPING,
                }
            ),
            interruption_state=(
                self._execution_state(state).value
                if self._execution_state(state)
                in {
                    SessionExecutionState.PAUSING,
                    SessionExecutionState.PAUSED,
                    SessionExecutionState.RESUMING,
                    SessionExecutionState.STOPPING,
                    SessionExecutionState.STOPPED,
                    SessionExecutionState.AWAITING_APPROVAL,
                }
                else None
            ),
            notes=(
                [policy.policy_hash()] if policy is not None else []
            )
            + ([str(state.get("last_error"))] if state.get("last_error") else []),
        )
        return model.model_dump(mode="json")

    def _status_payload(self, *, job: JobRun, state: dict[str, Any]) -> dict[str, Any]:
        return {
            "job": job.model_dump(mode="json"),
            "computer_use": state,
        }

    def _finalize(self, *, paths: TeamArtifactPaths, job: JobRun, events: list[TeamEvent]) -> None:
        write_audit_envelope(
            paths=paths,
            job=job,
            tasks=[],
            events=events,
            handoffs=[],
            policy_bundle_id="computer-use",
            policy_bundle_hash="computer-use",
            runtime_config_hash=self._config.profile_name,
            config=self._config,
        )


def _normalized_url_prefix(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return url
    path = parsed.path or "/"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def _surface_label(observation: SurfaceObservation) -> str | None:
    if observation.active_tab_url:
        return f"{observation.foreground_app or 'browser'}:{observation.active_tab_url}"
    if observation.focused_window_title:
        return (
            f"{observation.foreground_app or 'desktop'}:"
            f"{observation.focused_window_title}"
        )
    return observation.foreground_app


def _allowlisted_domains(actions: list[ProposedAction]) -> list[str]:
    domains: list[str] = []
    for action in actions:
        for candidate in [
            str(action.parameters.get("url") or ""),
            action.target_descriptor.current_url,
        ]:
            if not candidate or not candidate.startswith(("http://", "https://")):
                continue
            parsed = urlparse(candidate)
            if parsed.netloc and parsed.netloc not in domains:
                domains.append(parsed.netloc)
    return domains


def _action_payload(action: ProposedAction) -> dict[str, Any]:
    return {
        "action_id": action.action_id,
        "target_ref": action.target_descriptor.target_ref,
        "selector": action.target_descriptor.selector,
        "app_identity": action.app_identity,
        "risk_class": action.risk_class.value,
        "parameters": action.parameters,
    }
