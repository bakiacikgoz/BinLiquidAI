from __future__ import annotations

import hashlib
import json
import threading
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from binliquid.core.orchestrator import Orchestrator
from binliquid.runtime.config import RuntimeConfig
from binliquid.team.artifacts import (
    ensure_team_artifact_paths,
    write_audit_envelope,
    write_event,
    write_handoffs,
    write_status,
    write_task_runs,
)
from binliquid.team.checkpoint_store import TeamCheckpointStore
from binliquid.team.handoff import evaluate_handoff_transfer
from binliquid.team.memory_scope import evaluate_memory_scope_write, write_scoped_memory
from binliquid.team.models import (
    HandoffRecord,
    JobRun,
    JobStatus,
    TaskDefinition,
    TaskRun,
    TaskStatus,
    TeamEvent,
    TeamRunResult,
    TeamSpec,
)
from binliquid.team.scheduler import ParallelScheduler


class TeamSupervisor:
    def __init__(
        self,
        *,
        orchestrator: Orchestrator,
        config: RuntimeConfig,
    ):
        self._orchestrator = orchestrator
        self._config = config
        self._governance_runtime = getattr(orchestrator, "governance_runtime", None)
        self._memory_manager = getattr(orchestrator, "_memory_manager", None)

    def run(
        self,
        *,
        spec: TeamSpec,
        request: str,
        case_id: str | None = None,
        job_id: str | None = None,
        approval_overrides: dict[str, dict[str, str]] | None = None,
    ) -> TeamRunResult:
        created_at = datetime.now(UTC)
        resolved_case_id = case_id or f"case-{uuid4().hex[:12]}"
        resolved_job_id = job_id or f"job-{uuid4().hex[:12]}"
        job = JobRun(
            job_id=resolved_job_id,
            case_id=resolved_case_id,
            team_id=spec.team.team_id,
            request=request,
            status=JobStatus.RUNNING,
            created_at=created_at,
        )

        team_cfg = self._config.team
        paths = ensure_team_artifact_paths(
            job_id=resolved_job_id,
            root_dir=team_cfg.artifact_dir,
        )
        checkpoint_store = TeamCheckpointStore(team_cfg.checkpoint_db_path)
        events: list[TeamEvent] = []
        handoffs: list[HandoffRecord] = []
        task_outputs: dict[str, dict[str, Any]] = {}
        task_runs: dict[str, TaskRun] = {}
        lock = threading.Lock()

        def emit(
            event: str,
            *,
            task_id: str | None = None,
            agent_id: str | None = None,
            role: str | None = None,
            data: dict[str, Any] | None = None,
        ) -> None:
            entry = TeamEvent(
                event=event,
                team_id=spec.team.team_id,
                case_id=resolved_case_id,
                job_id=resolved_job_id,
                task_id=task_id,
                agent_id=agent_id,
                role=role,
                data=data or {},
            )
            with lock:
                events.append(entry)
                write_event(paths, entry)

        emit("team_start", data={"request": request})
        checkpoint_store.upsert(
            job_id=resolved_job_id,
            case_id=resolved_case_id,
            team_id=spec.team.team_id,
            status=job.status.value,
            payload={"phase": "started"},
        )

        tasks = _resolve_tasks(spec, request)
        if len(tasks) > spec.team.termination_rules.max_tasks:
            job.status = JobStatus.FAILED
            job.finished_at = datetime.now(UTC)
            job.final_output = "Team task budget exceeded."
            emit("team_final", data={"reason_code": "TEAM_BUDGET_EXCEEDED"})
            write_status(
                paths,
                {
                    "job": job.model_dump(mode="json"),
                    "reason_code": "TEAM_BUDGET_EXCEEDED",
                },
            )
            checkpoint_store.upsert(
                job_id=resolved_job_id,
                case_id=resolved_case_id,
                team_id=spec.team.team_id,
                status=job.status.value,
                payload={"reason_code": "TEAM_BUDGET_EXCEEDED"},
            )
            checkpoint_store.close()
            return TeamRunResult(job=job, tasks=[], events=events, handoffs=[])

        for item in tasks:
            emit(
                "task_created",
                task_id=item.task_id,
                role=item.role,
                data={
                    "task_type": item.task_type,
                    "depends_on": item.depends_on,
                },
            )

        scheduler = ParallelScheduler(
            max_parallel_tasks=max(1, _team_parallelism(self._config)),
            max_total_tasks=max(1, spec.team.termination_rules.max_tasks),
        )

        tasks_by_id = {item.task_id: item for item in tasks}
        if approval_overrides:
            for task_id, target_map in sorted(approval_overrides.items()):
                task_def = tasks_by_id.get(task_id)
                for target, approval_id in sorted(target_map.items()):
                    emit(
                        "approval_resolved",
                        task_id=task_id,
                        role=task_def.role if task_def else None,
                        data={
                            "approval_id": approval_id,
                            "status": "approved",
                            "target": target,
                        },
                    )

        def execute_task(task_def: TaskDefinition) -> TaskRun:
            agent = _select_agent(spec, task_def.role)
            emit(
                "task_assigned",
                task_id=task_def.task_id,
                role=task_def.role,
                agent_id=agent.agent_id,
                data={"task_type": task_def.task_type},
            )

            if agent.allowed_task_types and task_def.task_type not in agent.allowed_task_types:
                return TaskRun(
                    task_id=task_def.task_id,
                    assigned_agent_id=agent.agent_id,
                    role=task_def.role,
                    input_payload={},
                    status=TaskStatus.BLOCKED,
                    reason_code="TASK_ESCALATED",
                    approval_state="none",
                )

            dependency_snippets: list[str] = []
            for dep_id in task_def.depends_on:
                dep_output = task_outputs.get(dep_id)
                dep_task = tasks_by_id.get(dep_id)
                if dep_output is None or dep_task is None:
                    return TaskRun(
                        task_id=task_def.task_id,
                        assigned_agent_id=agent.agent_id,
                        role=task_def.role,
                        input_payload={},
                        status=TaskStatus.BLOCKED,
                        reason_code="TEAM_DEADLOCK",
                    )

                handoff = evaluate_handoff_transfer(
                    governance_runtime=self._governance_runtime,
                    run_id=resolved_job_id,
                    from_role=dep_task.role,
                    to_role=task_def.role,
                    payload=dep_output,
                    override_approval_id=_task_override(
                        approval_overrides,
                        task_id=task_def.task_id,
                        target="handoff",
                    ),
                )
                handoff_record = HandoffRecord(
                    from_agent=str(dep_output.get("agent_id", "unknown")),
                    to_agent=agent.agent_id,
                    payload=handoff.payload,
                    payload_hash=handoff.payload_hash,
                    policy_decision=handoff.reason_code,
                    redaction_applied=handoff.redaction_applied,
                    approval_id=handoff.approval_id,
                )
                with lock:
                    handoffs.append(handoff_record)

                emit(
                    "handoff",
                    task_id=task_def.task_id,
                    agent_id=agent.agent_id,
                    role=task_def.role,
                    data={
                        "from_task_id": dep_id,
                        "from_role": dep_task.role,
                        "to_role": task_def.role,
                        "policy_decision": handoff.reason_code,
                        "approval_id": handoff.approval_id,
                        "payload_hash": handoff.payload_hash,
                    },
                )

                if handoff.requires_approval:
                    emit(
                        "approval_requested",
                        task_id=task_def.task_id,
                        agent_id=agent.agent_id,
                        role=task_def.role,
                        data={
                            "approval_id": handoff.approval_id,
                            "reason_code": "TASK_ESCALATED",
                            "target": "handoff",
                        },
                    )
                    return TaskRun(
                        task_id=task_def.task_id,
                        assigned_agent_id=agent.agent_id,
                        role=task_def.role,
                        input_payload={},
                        status=TaskStatus.ESCALATED,
                        reason_code="TASK_ESCALATED",
                        approval_state="pending",
                    )
                if not handoff.allowed:
                    return TaskRun(
                        task_id=task_def.task_id,
                        assigned_agent_id=agent.agent_id,
                        role=task_def.role,
                        input_payload={},
                        status=TaskStatus.BLOCKED,
                        reason_code="HANDOFF_DENY",
                    )

                dependency_snippets.append(str(handoff.payload.get("output", "")))

            task_input = _build_task_input(
                request=request,
                task=task_def,
                dependency_snippets=dependency_snippets,
            )

            started_at = datetime.now(UTC)
            session_context = {
                "session_id": resolved_job_id,
                "team_id": spec.team.team_id,
                "case_id": resolved_case_id,
                "job_id": resolved_job_id,
                "task_id": task_def.task_id,
                "agent_id": agent.agent_id,
                "role": task_def.role,
            }
            task_override = _task_override(
                approval_overrides,
                task_id=task_def.task_id,
                target="task",
            )
            if task_override:
                session_context["governance_approval_id"] = task_override
            if (
                task_def.task_type == "chat"
                and _is_team_fast_chat_candidate(task_input)
                and hasattr(self._orchestrator, "process_fast_chat")
            ):
                result = self._orchestrator.process_fast_chat(
                    task_input,
                    session_context=session_context,
                    stream=False,
                    candidate_reason="team_chat_task",
                )
            else:
                result = self._orchestrator.process(
                    task_input,
                    session_context=session_context,
                    use_router=True,
                )
            finished_at = datetime.now(UTC)

            status = TaskStatus.COMPLETED
            reason_code = None
            approval_state = "none"
            if result.used_path == "governance_pending":
                status = TaskStatus.ESCALATED
                reason_code = "TASK_ESCALATED"
                approval_state = "pending"
                approval_id = str(result.metrics.get("approval_id") or "").strip()
                if approval_id:
                    emit(
                        "approval_requested",
                        task_id=task_def.task_id,
                        agent_id=agent.agent_id,
                        role=task_def.role,
                        data={
                            "approval_id": approval_id,
                            "reason_code": "TASK_ESCALATED",
                            "target": "task",
                        },
                    )
            elif result.used_path == "governance_blocked":
                status = TaskStatus.BLOCKED
                reason_code = str(result.metrics.get("governance_reason_code", "POLICY_DENY"))

            scope_decision = evaluate_memory_scope_write(
                governance_runtime=self._governance_runtime,
                run_id=resolved_job_id,
                scope="case",
                producer_role=task_def.role,
                visibility="team",
                override_approval_id=_task_override(
                    approval_overrides,
                    task_id=task_def.task_id,
                    target="memory_write",
                ),
            )
            emit(
                "memory_write_attempt",
                task_id=task_def.task_id,
                agent_id=agent.agent_id,
                role=task_def.role,
                data={"scope": "case", "reason_code": scope_decision.reason_code},
            )
            if scope_decision.requires_approval:
                emit(
                    "memory_write_blocked",
                    task_id=task_def.task_id,
                    agent_id=agent.agent_id,
                    role=task_def.role,
                    data={
                        "reason_code": "TASK_ESCALATED",
                        "approval_id": scope_decision.approval_id,
                    },
                )
                emit(
                    "approval_requested",
                    task_id=task_def.task_id,
                    agent_id=agent.agent_id,
                    role=task_def.role,
                    data={
                        "approval_id": scope_decision.approval_id,
                        "reason_code": "TASK_ESCALATED",
                        "target": "memory_write",
                    },
                )
                if status == TaskStatus.COMPLETED:
                    status = TaskStatus.ESCALATED
                    reason_code = "TASK_ESCALATED"
                    approval_state = "pending"
            elif not scope_decision.allowed:
                emit(
                    "memory_write_blocked",
                    task_id=task_def.task_id,
                    agent_id=agent.agent_id,
                    role=task_def.role,
                    data={"reason_code": "MEMORY_SCOPE_DENY"},
                )
                if status == TaskStatus.COMPLETED:
                    status = TaskStatus.BLOCKED
                    reason_code = "MEMORY_SCOPE_DENY"
            else:
                _ = write_scoped_memory(
                    memory_manager=self._memory_manager,
                    session_id=resolved_job_id,
                    task_type=task_def.task_type,
                    user_input=task_input,
                    assistant_output=result.final_text,
                    scope="case",
                    team_id=spec.team.team_id,
                    case_id=resolved_case_id,
                    job_id=resolved_job_id,
                    producer_agent_id=agent.agent_id,
                    producer_role=task_def.role,
                    visibility="team",
                )

            run = TaskRun(
                task_id=task_def.task_id,
                assigned_agent_id=agent.agent_id,
                role=task_def.role,
                input_payload={"input": task_input},
                status=status,
                attempt_count=1,
                approval_state=approval_state,
                result_payload={
                    "output": result.final_text,
                    "metrics": result.metrics,
                    "trace_id": result.trace_id,
                    "agent_id": agent.agent_id,
                },
                reason_code=reason_code,
                started_at=started_at,
                finished_at=finished_at,
            )

            if status == TaskStatus.COMPLETED:
                with lock:
                    task_outputs[task_def.task_id] = {
                        "output": result.final_text,
                        "trace_id": result.trace_id,
                        "agent_id": agent.agent_id,
                    }
                    task_runs[task_def.task_id] = run
            else:
                with lock:
                    task_runs[task_def.task_id] = run
            return run

        scheduler_result = scheduler.run(tasks=tasks, execute_task=execute_task)
        ordered_runs = scheduler_result.tasks

        last_completed = [item for item in ordered_runs if item.status == TaskStatus.COMPLETED]
        final_output = last_completed[-1].result_payload.get("output") if last_completed else None

        has_failed_tasks = any(item.status == TaskStatus.FAILED for item in ordered_runs)
        has_blocked_tasks = any(
            item.status in {TaskStatus.BLOCKED, TaskStatus.ESCALATED}
            for item in ordered_runs
        )
        if scheduler_result.reason_code == "TEAM_DEADLOCK" or has_failed_tasks:
            job.status = JobStatus.FAILED
        elif has_blocked_tasks:
            job.status = JobStatus.BLOCKED
        else:
            job.status = JobStatus.COMPLETED

        job.finished_at = datetime.now(UTC)
        job.final_output = str(final_output) if final_output is not None else ""
        completed_count = len(
            [item for item in ordered_runs if item.status == TaskStatus.COMPLETED]
        )
        blocked_count = len(
            [
                item
                for item in ordered_runs
                if item.status in {TaskStatus.BLOCKED, TaskStatus.ESCALATED}
            ]
        )
        failed_count = len([item for item in ordered_runs if item.status == TaskStatus.FAILED])
        job.metrics = {
            "task_count": len(ordered_runs),
            "completed_count": completed_count,
            "blocked_count": blocked_count,
            "failed_count": failed_count,
            "reason_code": scheduler_result.reason_code,
        }

        emit(
            "team_final",
            data={
                "status": job.status.value,
                "reason_code": scheduler_result.reason_code,
                "task_count": len(ordered_runs),
            },
        )

        write_task_runs(paths, ordered_runs)
        write_handoffs(paths, handoffs)

        policy_bundle = getattr(self._governance_runtime, "_policy_bundle", None)  # noqa: SLF001
        policy_bundle_id = "disabled"
        policy_bundle_hash = "disabled"
        if policy_bundle is not None:
            policy_bundle_id = str(getattr(policy_bundle.policy, "policy_version", "unknown"))
            policy_bundle_hash = str(getattr(policy_bundle, "policy_hash", "unknown"))

        envelope_path = write_audit_envelope(
            paths=paths,
            job=job,
            tasks=ordered_runs,
            events=events,
            handoffs=handoffs,
            policy_bundle_id=policy_bundle_id,
            policy_bundle_hash=policy_bundle_hash,
            runtime_config_hash=_runtime_config_hash(self._config),
        )

        status_payload = {
            "job": job.model_dump(mode="json"),
            "tasks": [item.model_dump(mode="json") for item in ordered_runs],
            "audit_envelope_path": envelope_path,
            "job_dir": str(paths.job_dir),
        }
        write_status(paths, status_payload)
        checkpoint_store.upsert(
            job_id=resolved_job_id,
            case_id=resolved_case_id,
            team_id=spec.team.team_id,
            status=job.status.value,
            payload={
                "reason_code": scheduler_result.reason_code,
                "task_count": len(ordered_runs),
                "audit_envelope_path": envelope_path,
            },
        )
        checkpoint_store.close()

        return TeamRunResult(
            job=job,
            tasks=ordered_runs,
            events=events,
            handoffs=handoffs,
            audit_envelope_path=envelope_path,
        )


def _resolve_tasks(spec: TeamSpec, request: str) -> list[TaskDefinition]:
    if spec.tasks:
        return spec.tasks

    role_index = _role_index(spec)
    intake = (
        role_index.get("intake agent")
        or role_index.get("case manager agent")
        or spec.team.agents[0].role
    )
    analyst = role_index.get("research analyst agent") or intake
    compliance = role_index.get("policy/compliance agent") or intake
    execution = role_index.get("execution agent") or intake
    reviewer = role_index.get("reviewer/qa agent") or intake

    complex_request = len(request.split()) >= 12
    if not complex_request:
        return [
            TaskDefinition(
                task_id="task-1",
                title="Single-pass response",
                task_type="chat",
                role=intake,
                depends_on=[],
                input_template="{{request}}",
            )
        ]

    return [
        TaskDefinition(
            task_id="task-1",
            title="Intake and normalization",
            task_type="plan",
            role=intake,
            depends_on=[],
            input_template="Normalize request for team execution: {{request}}",
        ),
        TaskDefinition(
            task_id="task-2",
            title="Research analysis",
            task_type="research",
            role=analyst,
            depends_on=["task-1"],
            input_template="Produce evidence and analysis from intake output.",
        ),
        TaskDefinition(
            task_id="task-3",
            title="Policy compliance check",
            task_type="plan",
            role=compliance,
            depends_on=["task-1"],
            input_template="Check policy and compliance constraints for the case.",
        ),
        TaskDefinition(
            task_id="task-4",
            title="Execution synthesis",
            task_type="mixed",
            role=execution,
            depends_on=["task-2", "task-3"],
            input_template="Synthesize actionable output from analysis + compliance.",
        ),
        TaskDefinition(
            task_id="task-5",
            title="Reviewer gate",
            task_type="chat",
            role=reviewer,
            depends_on=["task-4"],
            input_template="Review final output quality and safety; publish final response.",
        ),
    ]


def _build_task_input(
    *,
    request: str,
    task: TaskDefinition,
    dependency_snippets: list[str],
) -> str:
    body = task.input_template or task.title
    if "{{request}}" in body:
        body = body.replace("{{request}}", request)
    if dependency_snippets:
        deps = "\n\n".join(dependency_snippets)
        return f"{body}\n\nDependencies:\n{deps}"
    return body


def _select_agent(spec: TeamSpec, role: str):
    lowered = role.strip().lower()
    for agent in spec.team.agents:
        if agent.role.strip().lower() == lowered:
            return agent
    return spec.team.agents[0]


def _role_index(spec: TeamSpec) -> dict[str, str]:
    return {item.role.strip().lower(): item.role for item in spec.team.agents}


def _runtime_config_hash(config: RuntimeConfig) -> str:
    payload = config.model_dump(mode="json")
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _team_parallelism(config: RuntimeConfig) -> int:
    team_cfg = getattr(config, "team", None)
    if team_cfg is None:
        return 2
    return int(getattr(team_cfg, "max_parallel_tasks", 2))


def _task_override(
    approval_overrides: dict[str, dict[str, str]] | None,
    *,
    task_id: str,
    target: str,
) -> str | None:
    if approval_overrides is None:
        return None
    task_map = approval_overrides.get(task_id)
    if not isinstance(task_map, dict):
        return None
    value = task_map.get(target)
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    return normalized or None


def _is_team_fast_chat_candidate(text: str) -> bool:
    normalized = text.strip().lower()
    if not normalized:
        return False
    if len(normalized) > 64:
        return False
    if len(normalized.split()) > 10:
        return False
    heavy_tokens = {
        "kod",
        "python",
        "test",
        "debug",
        "araştır",
        "research",
        "tool",
        "benchmark",
        "lint",
        "diff",
    }
    return not any(token in normalized for token in heavy_tokens)
