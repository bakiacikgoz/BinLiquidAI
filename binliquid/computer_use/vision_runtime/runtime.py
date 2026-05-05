from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from binliquid.computer_use.vision_runtime.models import (
    StopDecision,
    VerificationResult,
    VisionAction,
    VisionPolicyDecision,
    VisionRunArtifact,
    VisionRunRequest,
    VisionStepResult,
)
from binliquid.computer_use.vision_runtime.policy import UniversalComputerUsePolicy
from binliquid.computer_use.vision_runtime.ports import (
    ActionPlannerPort,
    InputExecutorPort,
    ScreenCapturePort,
    StepVerifierPort,
    VisionAuditSink,
    VisionInterpreterPort,
)
from binliquid.computer_use.vision_runtime.recorder import RedactedVisionAuditRecorder
from binliquid.runtime.config import ComputerUseRuntimeConfig


class VisionComputerUseRuntime:
    def __init__(
        self,
        *,
        config: ComputerUseRuntimeConfig,
        artifact_root: Path,
        capture: ScreenCapturePort,
        vision: VisionInterpreterPort | None,
        planner: ActionPlannerPort,
        executor: InputExecutorPort,
        verifier: StepVerifierPort,
        audit: VisionAuditSink | None = None,
    ) -> None:
        self.config = config
        self.artifact_root = Path(artifact_root)
        self.capture = capture
        self.vision = vision
        self.planner = planner
        self.executor = executor
        self.verifier = verifier
        self.policy = UniversalComputerUsePolicy(config)
        self.audit = audit

    def run(self, request: VisionRunRequest) -> VisionRunArtifact:
        recorder = self.audit or RedactedVisionAuditRecorder(
            job_id=request.job_id,
            job_dir=self.artifact_root / request.job_id,
            runtime_config_hash=_hash_json(self.config.model_dump(mode="json")),
            policy_hash=self.policy.policy_hash,
        )
        if self.vision is None:
            envelope = recorder.finalize("failed")
            return self._artifact(
                request=request,
                status="failed",
                steps=[],
                envelope=envelope,
                stop_reason="VISION_PROVIDER_UNAVAILABLE",
            )

        steps: list[VisionStepResult] = []
        recovery_attempts = 0
        for step_index in range(self.config.max_steps):
            before = self.capture.capture()
            surface_stop = self.policy.detect_surface_stop(before, objective=request.objective)
            if surface_stop is not None:
                step = self._blocked_step(step_index, before.screenshot_hash, surface_stop)
                steps.append(step)
                recorder.record_step(step)
                envelope = recorder.finalize("failed")
                return self._artifact(
                    request=request,
                    status="failed",
                    steps=steps,
                    envelope=envelope,
                    stop_reason=surface_stop.reason_code,
                )

            interpretation = self.vision.interpret(
                objective=request.objective,
                observation=before,
                world=None,
            )
            action_or_stop = self.planner.next_action(
                objective=request.objective,
                interpretation=interpretation,
                world=None,
            )
            if isinstance(action_or_stop, StopDecision):
                envelope = recorder.finalize("completed")
                return self._artifact(
                    request=request,
                    status="completed",
                    steps=steps,
                    envelope=envelope,
                    stop_reason=action_or_stop.reason,
                )

            action = action_or_stop
            decision = self.policy.classify(action, before, mode=request.mode)
            if decision.denied:
                step = self._step(
                    step_index=step_index,
                    before_hash=before.screenshot_hash,
                    action=action,
                    decision=decision,
                    execution_status="blocked",
                )
                steps.append(step)
                recorder.record_step(step)
                envelope = recorder.finalize("failed")
                return self._artifact(
                    request=request,
                    status="failed",
                    steps=steps,
                    envelope=envelope,
                    stop_reason=decision.reason_code,
                )
            if decision.requires_approval:
                step = self._step(
                    step_index=step_index,
                    before_hash=before.screenshot_hash,
                    action=action,
                    decision=decision,
                    execution_status="approval_required",
                    approval_snapshot=self._approval_snapshot(
                        request=request,
                        step_index=step_index,
                        before_hash=before.screenshot_hash,
                        action=action,
                        decision=decision,
                    ),
                )
                steps.append(step)
                recorder.record_step(step)
                envelope = recorder.finalize("awaiting_approval")
                return self._artifact(
                    request=request,
                    status="awaiting_approval",
                    steps=steps,
                    envelope=envelope,
                )

            execution = self.executor.execute(action)
            if execution.status == "failed":
                verification = VerificationResult(
                    verified=False,
                    confidence=0.0,
                    message=execution.message or "execution failed",
                )
                step = self._step(
                    step_index=step_index,
                    before_hash=before.screenshot_hash,
                    action=action,
                    decision=decision,
                    execution_status="failed",
                    verification=verification,
                )
                steps.append(step)
                recorder.record_step(step)
                envelope = recorder.finalize("failed")
                return self._artifact(
                    request=request,
                    status="failed",
                    steps=steps,
                    envelope=envelope,
                    stop_reason="EXECUTION_FAILED",
                )

            after = self.capture.capture()
            verification = self.verifier.verify(before=before, action=action, after=after)
            step = self._step(
                step_index=step_index,
                before_hash=before.screenshot_hash,
                action=action,
                decision=decision,
                execution_status="executed",
                after_hash=after.screenshot_hash,
                verification=verification,
                checkpoint_id=f"{request.job_id}:{step_index}",
            )
            steps.append(step)
            recorder.record_step(step)
            if not verification.verified:
                if recovery_attempts >= self.config.max_recovery_attempts:
                    envelope = recorder.finalize("failed")
                    return self._artifact(
                        request=request,
                        status="failed",
                        steps=steps,
                        envelope=envelope,
                        stop_reason="VERIFICATION_FAILED",
                    )
                recovery_attempts += 1

        envelope = recorder.finalize("failed")
        return self._artifact(
            request=request,
            status="failed",
            steps=steps,
            envelope=envelope,
            stop_reason="MAX_STEPS_EXCEEDED",
        )

    def _blocked_step(
        self,
        step_index: int,
        before_hash: str,
        decision: VisionPolicyDecision,
    ) -> VisionStepResult:
        return self._step(
            step_index=step_index,
            before_hash=before_hash,
            action=VisionAction(
                action_id=f"blocked-{step_index}",
                action_type="wait",
                rationale="Policy blocked before action planning.",
                expected_effect="No action is executed.",
                risk_class="critical",
                requires_approval=False,
                confidence=1.0,
            ),
            decision=decision,
            execution_status="blocked",
        )

    @staticmethod
    def _step(
        *,
        step_index: int,
        before_hash: str,
        action: VisionAction,
        decision: VisionPolicyDecision,
        execution_status: str,
        after_hash: str | None = None,
        verification: VerificationResult | None = None,
        checkpoint_id: str | None = None,
        approval_snapshot: dict[str, Any] | None = None,
    ) -> VisionStepResult:
        return VisionStepResult(
            step_index=step_index,
            before_hash=before_hash,
            action=action,
            policy_decision=decision,
            execution_status=execution_status,
            after_hash=after_hash,
            verification=verification,
            checkpoint_id=checkpoint_id,
            approval_snapshot=approval_snapshot,
        )

    @staticmethod
    def _approval_snapshot(
        *,
        request: VisionRunRequest,
        step_index: int,
        before_hash: str,
        action: VisionAction,
        decision: VisionPolicyDecision,
    ) -> dict[str, Any]:
        action_payload = action.model_dump(mode="json", exclude_none=True)
        action_hash = _hash_json(action_payload)
        return {
            "kind": "computer_use_vision_action",
            "job_id": request.job_id,
            "step_index": step_index,
            "objective": request.objective,
            "before_screenshot_hash": before_hash,
            "target_bbox": action.target_bbox.model_dump(mode="json")
            if action.target_bbox is not None
            else None,
            "action_type": action.action_type.value,
            "expected_effect": action.expected_effect,
            "risk_class": action.risk_class.value,
            "risk_reasons": decision.risk_reasons,
            "policy_hash": decision.policy_hash,
            "execution_contract": {
                "action_hash": action_hash,
                "max_age_ms": 5000,
            },
        }

    @staticmethod
    def _artifact(
        *,
        request: VisionRunRequest,
        status: str,
        steps: list[VisionStepResult],
        envelope: dict[str, Any],
        stop_reason: str | None = None,
    ) -> VisionRunArtifact:
        return VisionRunArtifact(
            job_id=request.job_id,
            status=status,
            objective=request.objective,
            steps=steps,
            redaction_report=envelope.get("redaction_report", {}),
            integrity=envelope.get("integrity", {}),
            stop_reason=stop_reason,
        )


def _hash_json(payload: object) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()
