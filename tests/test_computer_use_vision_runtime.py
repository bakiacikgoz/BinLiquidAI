from __future__ import annotations

from dataclasses import dataclass

import binliquid.computer_use.runtime as computer_use_runtime
from binliquid.computer_use.models import ComputerUseMode, RiskClass
from binliquid.computer_use.vision_runtime.models import (
    ExecutionResult,
    InputActionType,
    NormalizedBBox,
    StopDecision,
    SurfaceKind,
    VerificationResult,
    VisionAction,
    VisionInterpretation,
    VisionObservation,
    VisionRunRequest,
)
from binliquid.computer_use.vision_runtime.providers.mock_vision import (
    DeterministicActionPlanner,
    DeterministicScreenCapture,
    DeterministicStepVerifier,
)
from binliquid.computer_use.vision_runtime.runtime import VisionComputerUseRuntime
from binliquid.runtime.config import ComputerUseRuntimeConfig, RuntimeConfig


def _observation(hash_char: str = "c") -> VisionObservation:
    return VisionObservation(
        screenshot_hash=hash_char * 64,
        captured_at="2026-05-05T00:00:00+00:00",
        platform="macos",
        active_app="Safari",
        surface_kind=SurfaceKind.BROWSER,
        confidence=0.92,
    )


def _action(
    *,
    action_type: InputActionType = InputActionType.WAIT,
    risk_class: RiskClass = RiskClass.LOW,
    requires_approval: bool = False,
) -> VisionAction:
    return VisionAction(
        action_id="act-1",
        action_type=action_type,
        target_bbox=NormalizedBBox(x=0.1, y=0.1, w=0.2, h=0.2),
        rationale="Advance deterministic test.",
        expected_effect="State changes.",
        risk_class=risk_class,
        requires_approval=requires_approval,
        confidence=0.9,
    )


@dataclass
class _Interpreter:
    def interpret(self, *, objective, observation, world):  # noqa: ANN001
        return VisionInterpretation(
            observation_hash=observation.screenshot_hash,
            summary=f"Objective: {objective}",
            candidate_actions=[_action()],
            confidence=0.91,
        )


class _Executor:
    def __init__(self) -> None:
        self.executed: list[VisionAction] = []

    def execute(self, action: VisionAction) -> ExecutionResult:
        self.executed.append(action)
        return ExecutionResult(status="executed", message="ok")


class _MacOSPlatform:
    label = "macos"
    system = "Darwin"
    machine = "arm64"
    release = "test"


def test_runtime_blocks_when_vision_provider_missing(tmp_path) -> None:
    runtime = VisionComputerUseRuntime(
        config=ComputerUseRuntimeConfig(runtime_mode="vision_first", vision_enabled=True),
        artifact_root=tmp_path,
        capture=DeterministicScreenCapture([_observation()]),
        vision=None,
        planner=DeterministicActionPlanner([_action()]),
        executor=_Executor(),
        verifier=DeterministicStepVerifier([VerificationResult(verified=True, confidence=0.9)]),
    )

    artifact = runtime.run(
        VisionRunRequest(
            job_id="job-vision-missing",
            objective="Read page",
            mode=ComputerUseMode.EXECUTE,
        )
    )

    assert artifact.status == "failed"
    assert artifact.stop_reason == "VISION_PROVIDER_UNAVAILABLE"
    assert artifact.redaction_report["raw_screenshot_persisted_count"] == 0


def test_runtime_completes_safe_mock_task_and_records_hash_chain(tmp_path) -> None:
    executor = _Executor()
    runtime = VisionComputerUseRuntime(
        config=ComputerUseRuntimeConfig(
            runtime_mode="vision_first",
            vision_enabled=True,
            max_steps=2,
        ),
        artifact_root=tmp_path,
        capture=DeterministicScreenCapture([_observation("c"), _observation("d")]),
        vision=_Interpreter(),
        planner=DeterministicActionPlanner([_action(), StopDecision(reason="done")]),
        executor=executor,
        verifier=DeterministicStepVerifier([VerificationResult(verified=True, confidence=0.9)]),
    )

    artifact = runtime.run(
        VisionRunRequest(job_id="job-complete", objective="Read page", mode=ComputerUseMode.EXECUTE)
    )

    assert artifact.status == "completed"
    assert len(artifact.steps) == 1
    assert executor.executed[0].action_type == InputActionType.WAIT
    assert artifact.integrity["hash_chain_verified"] is True


def test_runtime_returns_awaiting_approval_without_executing(tmp_path) -> None:
    executor = _Executor()
    config = ComputerUseRuntimeConfig(
        runtime_mode="vision_first",
        vision_enabled=True,
        approval_snapshot_max_age_ms=12345,
    )
    runtime = VisionComputerUseRuntime(
        config=config,
        artifact_root=tmp_path,
        capture=DeterministicScreenCapture([_observation()]),
        vision=_Interpreter(),
        planner=DeterministicActionPlanner(
            [_action(action_type=InputActionType.CLICK, risk_class=RiskClass.MEDIUM)]
        ),
        executor=executor,
        verifier=DeterministicStepVerifier([]),
    )

    artifact = runtime.run(
        VisionRunRequest(
            job_id="job-approval",
            objective="Click export",
            mode=ComputerUseMode.STEP_APPROVAL,
        )
    )

    assert artifact.status == "awaiting_approval"
    assert artifact.steps[0].execution_status == "approval_required"
    assert artifact.steps[0].approval_snapshot is not None
    assert artifact.steps[0].approval_snapshot["max_age_ms"] == 12345
    assert executor.executed == []


def test_runtime_stops_after_verification_failure_budget(tmp_path) -> None:
    runtime = VisionComputerUseRuntime(
        config=ComputerUseRuntimeConfig(
            runtime_mode="vision_first",
            vision_enabled=True,
            max_recovery_attempts=0,
        ),
        artifact_root=tmp_path,
        capture=DeterministicScreenCapture([_observation("c"), _observation("d")]),
        vision=_Interpreter(),
        planner=DeterministicActionPlanner([_action()]),
        executor=_Executor(),
        verifier=DeterministicStepVerifier(
            [VerificationResult(verified=False, confidence=0.3, message="state mismatch")]
        ),
    )

    artifact = runtime.run(
        VisionRunRequest(
            job_id="job-verify-fail",
            objective="Read page",
            mode=ComputerUseMode.EXECUTE,
        )
    )

    assert artifact.status == "failed"
    assert artifact.stop_reason == "COMPUTER_USE_RECOVERY_BUDGET_EXCEEDED"
    assert artifact.steps[0].verification is not None
    assert artifact.steps[0].verification.verified is False


def test_runner_ollama_vision_first_uses_candidate_action_planner(
    tmp_path,
    monkeypatch,
) -> None:
    class FakeCapture:
        def __init__(self, **_: object) -> None:
            pass

        def capture(self) -> VisionObservation:
            return _observation()

    class FakeOllamaVision:
        def __init__(self, **_: object) -> None:
            pass

        def interpret(self, *, objective, observation, world):  # noqa: ANN001
            del objective, world
            return VisionInterpretation(
                observation_hash=observation.screenshot_hash,
                summary="A submit button is visible.",
                candidate_actions=[
                    _action(action_type=InputActionType.CLICK, risk_class=RiskClass.MEDIUM)
                ],
                surface_kind=SurfaceKind.BROWSER,
                active_app_guess="Safari",
                confidence=0.93,
            )

    class FakeMacOSExecutor:
        def __init__(self, **_: object) -> None:
            self.executed: list[VisionAction] = []

        def execute(self, action: VisionAction) -> ExecutionResult:
            self.executed.append(action)
            return ExecutionResult(status="executed", message="ok")

    monkeypatch.setattr(computer_use_runtime, "current_platform", lambda: _MacOSPlatform())
    monkeypatch.setattr(computer_use_runtime, "MacOSScreenCaptureProvider", FakeCapture)
    monkeypatch.setattr(computer_use_runtime, "OllamaVisionInterpreter", FakeOllamaVision)
    monkeypatch.setattr(computer_use_runtime, "MacOSInputExecutor", FakeMacOSExecutor)

    runner = computer_use_runtime.ComputerUseRunner(
        config=RuntimeConfig(
            computer_use=ComputerUseRuntimeConfig(
                runtime_mode="vision_first",
                vision_enabled=True,
                vision_provider="ollama",
                vision_model="llava",
                action_set=["click"],
                max_steps=1,
            )
        ),
        root_dir=tmp_path,
    )

    payload = runner.run(
        prompt="Submit safe fixture",
        job_id="job-ollama-candidate",
        mode=ComputerUseMode.STEP_APPROVAL,
        runtime_mode="vision_first",
    )

    assert payload["job"]["status"] == "awaiting_approval"
    assert payload["computer_use"]["steps"][0]["action"]["action_type"] == "click"
