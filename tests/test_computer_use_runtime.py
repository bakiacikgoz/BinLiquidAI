from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from binliquid.computer_use.adapters import BrowserAdapter, FileDialogAdapter, WindowMetadata
from binliquid.computer_use.models import (
    BrowserTaskFamily,
    ComputerUseMode,
    EvidenceEnvelope,
    PerceptionSnapshot,
    PerceptionSource,
    ProposedAction,
    SelectorContext,
    SessionExecutionState,
    SurfaceObservation,
    TargetDescriptor,
    VerificationResult,
)
from binliquid.computer_use.perception import build_perception_fingerprint
from binliquid.computer_use.prompt_parser import parse_prompt_to_actions
from binliquid.computer_use.runtime import (
    ComputerUseRunner,
    RuntimeAdapters,
    SessionCommand,
    SessionControlBus,
)
from binliquid.runtime.config import RuntimeConfig


def _wait_until(predicate, timeout_s: float = 5.0) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    raise AssertionError("timed out waiting for predicate")


def _read_event_names(events_path: Path) -> list[str]:
    return [event["event"] for event in _read_events(events_path)]


def _read_events(events_path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in events_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


class _FakeDesktopAdapter:
    def __init__(self) -> None:
        self._frontmost = "Safari"
        self._dialog_open = False
        self._window_titles = {
            "Safari": "Safari window",
            "Notes": "Notes window",
        }
        self._bundle_ids = {
            "Safari": "com.apple.Safari",
            "Notes": "com.apple.Notes",
        }

    def launch_app(self, app_name: str) -> None:
        self._frontmost = app_name

    def focus_window(self, app_name: str) -> None:
        self._frontmost = app_name

    def frontmost_app(self) -> str:
        return self._frontmost

    def set_frontmost(self, app_name: str) -> None:
        self._frontmost = app_name

    def set_dialog_open(self, value: bool) -> None:
        self._dialog_open = value

    def bundle_id(self, app_name: str) -> str | None:
        return self._bundle_ids.get(app_name)

    def inspect_windows(self, app_name: str) -> list[WindowMetadata]:
        if app_name != self._frontmost and app_name != "Safari":
            return []
        return [
            WindowMetadata(
                app_name=app_name,
                window_title=self._window_titles.get(app_name, f"{app_name} window"),
                focused=app_name == self._frontmost,
                dialog_open=self._dialog_open if app_name == self._frontmost else False,
                bundle_id=self.bundle_id(app_name),
            )
        ]

    def detect_dialog(self, app_name: str) -> bool:
        return app_name == self._frontmost and self._dialog_open

    def observe_surface(self, app_name: str | None = None) -> SurfaceObservation:
        target_app = self._frontmost or app_name or "Safari"
        return SurfaceObservation(
            foreground_app=self._frontmost,
            bundle_id=self.bundle_id(self._frontmost),
            focused_window_title=self._window_titles.get(target_app, f"{target_app} window"),
            modal_detected=self._dialog_open,
            visible_selectors=None,
            captured_at="2026-03-14T00:00:00+00:00",
        )


class _FakeBrowserAdapter(BrowserAdapter):
    adapter_status = "fake_runtime"

    def __init__(
        self,
        *,
        desktop: _FakeDesktopAdapter,
        on_verified=None,
        surface_url_overrides: dict[int, str] | None = None,
        hidden_selectors_on_observe: dict[int, set[str]] | None = None,
        modal_on_observe: set[int] | None = None,
        create_download_artifact: bool = True,
        omit_selected_file_result: bool = False,
        wait_delay_s: float | None = None,
    ) -> None:
        self._desktop = desktop
        self._current_url = "about:blank"
        self._title = "Fake Browser"
        self._values: dict[str, str] = {}
        self._on_verified = on_verified
        self._observe_count = 0
        self._surface_url_overrides = dict(surface_url_overrides or {})
        self._hidden_selectors_on_observe = {
            key: set(value) for key, value in (hidden_selectors_on_observe or {}).items()
        }
        self._modal_on_observe = set(modal_on_observe or ())
        self._create_download_artifact = create_download_artifact
        self._omit_selected_file_result = omit_selected_file_result
        self._wait_delay_s = wait_delay_s

    def observe_surface(self, *, target: TargetDescriptor | None = None) -> SurfaceObservation:
        self._observe_count += 1
        selector = target.selector if target is not None else None
        current_url = self._surface_url_overrides.get(self._observe_count, self._current_url)
        visible_selectors: list[str] | None = None
        if selector and selector not in {"document", "window"}:
            hidden = self._hidden_selectors_on_observe.get(self._observe_count, set())
            visible_selectors = [] if selector in hidden else [selector]
        return SurfaceObservation(
            foreground_app=self._desktop.frontmost_app(),
            bundle_id=self._desktop.bundle_id("Safari"),
            focused_window_title="Safari window",
            active_tab_url=current_url,
            active_tab_title=self._title if current_url == self._current_url else "Drifted page",
            modal_detected=self._observe_count in self._modal_on_observe,
            visible_selectors=visible_selectors,
            captured_at="2026-03-14T00:00:00+00:00",
        )

    def inspect_target(self, *, target: TargetDescriptor) -> PerceptionSnapshot:
        selector_context = SelectorContext(
            selector=target.selector,
            selector_source=target.selector_source,
            selector_trace=[target.selector],
        )
        fingerprint = build_perception_fingerprint(
            window_or_tab_identity="safari:fake",
            app_identity="browser:safari",
            selector_context=selector_context.model_dump(mode="json"),
            screenshot_hash=f"{target.selector}:{self._current_url}",
        )
        return PerceptionSnapshot(
            source=PerceptionSource.DOM,
            confidence=0.99,
            perception_fingerprint=fingerprint,
            sensitive_surface=False,
            focused=self._desktop.frontmost_app() == "Safari",
            unexpected_modal=False,
            selector_ambiguous=False,
            window_or_tab_identity="safari:fake",
            app_identity="browser:safari",
            current_url=self._current_url,
            selector_context=selector_context,
            evidence=EvidenceEnvelope(
                screenshot_hash="shot-hash-runtime",
                redacted_fingerprint="fingerprint-runtime",
                accessibility_subset={
                    "title": self._title,
                    "value": self._values.get(target.selector, ""),
                },
            ),
        )

    def execute(self, *, action: ProposedAction) -> dict[str, str]:
        self._desktop.focus_window("Safari")
        if action.action_id == "open_url":
            self._current_url = str(
                action.parameters.get("url") or action.target_descriptor.current_url
            )
            self._title = "Opened"
            return {"status": "executed", "url": self._current_url, "title": self._title}
        if action.action_id == "type_text":
            text = str(action.parameters.get("text") or "")
            self._values[action.target_descriptor.selector] = text
            return {"status": "executed", "value": text}
        if action.action_id == "click":
            self._values[action.target_descriptor.selector] = "clicked"
            return {"status": "executed"}
        if action.action_id == "select_option":
            value = str(action.parameters.get("value") or "")
            self._values[action.target_descriptor.selector] = value
            return {"status": "executed", "value": value}
        if action.action_id == "upload_file":
            selected_path = str(action.parameters.get("path") or "")
            self._values[action.target_descriptor.selector] = Path(selected_path).name
            result = {
                "status": "executed",
                "selected_file_name": Path(selected_path).name,
                "dialog_interacted": True,
            }
            if not self._omit_selected_file_result:
                result["selected_file"] = selected_path
            return result
        if action.action_id == "download_file":
            output_path = str(action.parameters.get("output_path") or "")
            if output_path and self._create_download_artifact:
                Path(output_path).parent.mkdir(parents=True, exist_ok=True)
                Path(output_path).write_text("download artifact", encoding="utf-8")
            result = {"status": "executed", "download_triggered": True}
            if output_path and self._create_download_artifact:
                result["download_path"] = output_path
            return result
        if action.action_id == "wait":
            seconds = float(action.parameters.get("seconds") or 0.0)
            time.sleep(self._wait_delay_s if self._wait_delay_s is not None else seconds)
            return {"status": "executed"}
        raise RuntimeError(f"unsupported action in fake adapter: {action.action_id}")

    def verify(
        self,
        *,
        action: ProposedAction,
        before: PerceptionSnapshot | None = None,
    ) -> VerificationResult:
        del before
        kind = action.verification_kind
        expected = action.verification_value or ""
        if kind == "url":
            verified = self._current_url.startswith(expected)
            result = VerificationResult(
                verified=verified,
                kind="url",
                summary="URL matches the requested destination." if verified else "URL mismatch.",
                expected={"url": expected},
                observed={"url": self._current_url},
                mismatch_code=None if verified else "url_mismatch",
                retryable=not verified,
            )
        elif kind == "value":
            current = self._values.get(action.target_descriptor.selector, "")
            verified = current == expected
            result = VerificationResult(
                verified=verified,
                kind="value",
                summary="Value matches expected input." if verified else "Value mismatch.",
                expected={"value": expected},
                observed={"value": current},
                mismatch_code=None if verified else "value_mismatch",
                retryable=not verified,
            )
        elif kind == "selector_present":
            result = VerificationResult(
                verified=True,
                kind="selector_present",
                summary="Selector remained present after click.",
                expected={"selector_count": 1},
                observed={"selector_count": 1, "state_change": True},
            )
        else:
            result = VerificationResult(
                verified=True,
                kind=kind or "none",
                summary="Verification passed.",
            )
        if result.verified and self._on_verified is not None:
            self._on_verified(action)
        return result


class _FailingClickBrowserAdapter(_FakeBrowserAdapter):
    def verify(
        self,
        *,
        action: ProposedAction,
        before: PerceptionSnapshot | None = None,
    ) -> VerificationResult:
        if action.verification_kind == "selector_present":
            return VerificationResult(
                verified=False,
                kind="selector_present",
                summary="Click did not cause a visible state change.",
                expected={"state_change": True},
                observed={"state_change": False},
                mismatch_code="no_state_change_after_click",
                retryable=True,
            )
        return super().verify(action=action, before=before)


def test_prompt_parser_builds_an_automation_sequence() -> None:
    family, actions = parse_prompt_to_actions(
        prompt=(
            'launch "Safari"\n'
            'open "https://ops.example.internal/queue"\n'
            'type "Aegis" into "#name"'
        ),
        mode=ComputerUseMode.EXECUTE,
    )

    assert family == BrowserTaskFamily.AUTOMATION_SEQUENCE
    assert [item.action_id for item in actions] == ["launch_app", "open_url", "type_text"]
    assert actions[1].verification_kind == "url"
    assert actions[2].parameters["text"] == "Aegis"


def test_session_control_bus_round_trips_commands(tmp_path: Path) -> None:
    job_dir = tmp_path / "job-control"
    job_dir.mkdir()
    bus = SessionControlBus(job_dir)

    bus.write(SessionCommand.PAUSE, reason="operator_pause")
    paused = bus.read()
    assert paused.command == SessionCommand.PAUSE
    assert paused.reason == "operator_pause"

    bus.clear()
    assert bus.read().command == SessionCommand.RUN


def test_computer_use_runner_executes_a_real_runtime_slice_with_fake_adapters(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "jobs"
    config = RuntimeConfig.from_profile("default")
    desktop = _FakeDesktopAdapter()
    browser = _FakeBrowserAdapter(desktop=desktop)
    runner = ComputerUseRunner(
        config=config,
        root_dir=root_dir,
        adapters=RuntimeAdapters(
            browser=browser,
            desktop=desktop,
            dialog=FileDialogAdapter(allowed_roots=[tmp_path]),
        ),
    )

    payload = runner.run(
        prompt='open "https://ops.example.internal/queue"\ntype "Aegis Operator" into "#name"',
        job_id="job-runtime-complete",
        mode=ComputerUseMode.EXECUTE,
    )

    assert payload["job"]["status"] == "completed"
    status_payload = json.loads(
        (root_dir / "job-runtime-complete" / "status.json").read_text(encoding="utf-8")
    )
    assert status_payload["computer_use"]["lifecycle_state"] == "completed"
    assert (
        status_payload["computer_use"]["world_model"]["current_url"]
        == "https://ops.example.internal/queue"
    )
    assert status_payload["computer_use"]["last_verification_result"]["kind"] == "value"
    assert status_payload["computer_use"]["expected_surface"]["app_name"] == "Safari"
    assert status_payload["computer_use"]["surface_mismatch"] is None
    assert (
        status_payload["computer_use"]["world_model"]["observed_surface"]["active_tab_url"]
        == "https://ops.example.internal/queue"
    )
    event_names = _read_event_names(root_dir / "job-runtime-complete" / "events.jsonl")
    assert "action_verified" in event_names
    assert "session_completed" in event_names


def test_computer_use_runner_fails_closed_on_wrong_tab_drift(tmp_path: Path) -> None:
    root_dir = tmp_path / "jobs"
    config = RuntimeConfig.from_profile("default")
    desktop = _FakeDesktopAdapter()
    runner = ComputerUseRunner(
        config=config,
        root_dir=root_dir,
        adapters=RuntimeAdapters(
            browser=_FakeBrowserAdapter(
                desktop=desktop,
                surface_url_overrides={3: "https://drift.example.internal/review"},
            ),
            desktop=desktop,
            dialog=FileDialogAdapter(allowed_roots=[tmp_path]),
        ),
    )

    payload = runner.run(
        prompt='open "https://ops.example.internal/queue"\ntype "Aegis Operator" into "#name"',
        job_id="job-runtime-wrong-tab",
        mode=ComputerUseMode.EXECUTE,
    )

    assert payload["job"]["status"] == "failed"
    status_payload = json.loads(
        (root_dir / "job-runtime-wrong-tab" / "status.json").read_text(encoding="utf-8")
    )
    assert status_payload["computer_use"]["surface_mismatch"]["code"] == "wrong_tab"
    assert status_payload["computer_use"]["last_verification_result"]["mismatch_code"] == (
        "wrong_tab"
    )
    assert (
        status_payload["computer_use"]["observed_surface"]["active_tab_url"]
        == "https://drift.example.internal/review"
    )
    events = _read_events(root_dir / "job-runtime-wrong-tab" / "events.jsonl")
    mismatch_events = [
        event for event in events if event["event"] == "computer_use.surface_mismatch"
    ]
    assert len(mismatch_events) == 1
    mismatch_data = mismatch_events[0]["data"]
    assert mismatch_data["reason_code"] == "wrong_tab"
    assert mismatch_data["observed_surface"]["active_tab_url"] == (
        "https://drift.example.internal/review"
    )
    assert mismatch_data["expected_surface"]["tab_url_host"] == "ops.example.internal"


def test_computer_use_runner_fails_closed_on_wrong_foreground_app(tmp_path: Path) -> None:
    root_dir = tmp_path / "jobs"
    config = RuntimeConfig.from_profile("default")
    desktop = _FakeDesktopAdapter()
    desktop.set_frontmost("Notes")
    runner = ComputerUseRunner(
        config=config,
        root_dir=root_dir,
        adapters=RuntimeAdapters(
            browser=_FakeBrowserAdapter(desktop=desktop),
            desktop=desktop,
            dialog=FileDialogAdapter(allowed_roots=[tmp_path]),
        ),
    )

    payload = runner.run(
        prompt='type "Aegis Operator" into "#name"',
        job_id="job-runtime-wrong-app",
        mode=ComputerUseMode.EXECUTE,
    )

    assert payload["job"]["status"] == "failed"
    status_payload = json.loads(
        (root_dir / "job-runtime-wrong-app" / "status.json").read_text(encoding="utf-8")
    )
    assert status_payload["computer_use"]["surface_mismatch"]["code"] == "wrong_app"
    assert status_payload["computer_use"]["observed_surface"]["foreground_app"] == "Notes"


def test_computer_use_runner_fails_closed_on_unexpected_modal(tmp_path: Path) -> None:
    root_dir = tmp_path / "jobs"
    config = RuntimeConfig.from_profile("default")
    desktop = _FakeDesktopAdapter()
    runner = ComputerUseRunner(
        config=config,
        root_dir=root_dir,
        adapters=RuntimeAdapters(
            browser=_FakeBrowserAdapter(desktop=desktop, modal_on_observe={1}),
            desktop=desktop,
            dialog=FileDialogAdapter(allowed_roots=[tmp_path]),
        ),
    )

    payload = runner.run(
        prompt='type "Aegis Operator" into "#name"',
        job_id="job-runtime-modal",
        mode=ComputerUseMode.EXECUTE,
    )

    assert payload["job"]["status"] == "failed"
    status_payload = json.loads(
        (root_dir / "job-runtime-modal" / "status.json").read_text(encoding="utf-8")
    )
    assert status_payload["computer_use"]["surface_mismatch"]["code"] == "unexpected_modal"


def test_computer_use_runner_fails_closed_on_missing_expected_selector(tmp_path: Path) -> None:
    root_dir = tmp_path / "jobs"
    config = RuntimeConfig.from_profile("default")
    desktop = _FakeDesktopAdapter()
    runner = ComputerUseRunner(
        config=config,
        root_dir=root_dir,
        adapters=RuntimeAdapters(
            browser=_FakeBrowserAdapter(
                desktop=desktop,
                hidden_selectors_on_observe={1: {"#name"}},
            ),
            desktop=desktop,
            dialog=FileDialogAdapter(allowed_roots=[tmp_path]),
        ),
    )

    payload = runner.run(
        prompt='type "Aegis Operator" into "#name"',
        job_id="job-runtime-missing-selector",
        mode=ComputerUseMode.EXECUTE,
    )

    assert payload["job"]["status"] == "failed"
    status_payload = json.loads(
        (root_dir / "job-runtime-missing-selector" / "status.json").read_text(
            encoding="utf-8"
        )
    )
    assert status_payload["computer_use"]["surface_mismatch"]["code"] == (
        "missing_expected_selector"
    )


def test_computer_use_runner_verifies_allowed_root_upload_and_serializes_artifact(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "jobs"
    upload_path = tmp_path / "upload.txt"
    upload_path.write_text("upload fixture", encoding="utf-8")
    config = RuntimeConfig.from_profile("default")
    desktop = _FakeDesktopAdapter()
    runner = ComputerUseRunner(
        config=config,
        root_dir=root_dir,
        adapters=RuntimeAdapters(
            browser=_FakeBrowserAdapter(desktop=desktop),
            desktop=desktop,
            dialog=FileDialogAdapter(allowed_roots=[tmp_path]),
        ),
    )

    payload = runner.run(
        prompt=(
            'open "https://ops.example.internal/queue"\n'
            f'upload "{upload_path}" to "#upload"'
        ),
        job_id="job-runtime-upload-success",
        mode=ComputerUseMode.EXECUTE,
    )

    assert payload["job"]["status"] == "completed"
    status_payload = json.loads(
        (root_dir / "job-runtime-upload-success" / "status.json").read_text(
            encoding="utf-8"
        )
    )
    verification = status_payload["computer_use"]["last_verification_result"]
    assert verification["expected_file_operation"]["operation"] == "upload"
    assert verification["observed_file_operation"]["resolved_path"] == str(upload_path.resolve())
    assert verification["file_operation_mismatch"] is None
    assert status_payload["computer_use"]["artifacts"]["upload_file"]["selected_file"] == str(
        upload_path
    )
    event_names = _read_event_names(root_dir / "job-runtime-upload-success" / "events.jsonl")
    assert "computer_use.file_operation_verified" in event_names


def test_computer_use_runner_fails_closed_on_upload_path_outside_allowed_roots(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "jobs"
    outside_path = tmp_path.parent / "outside-upload.txt"
    outside_path.write_text("outside root", encoding="utf-8")
    config = RuntimeConfig.from_profile("default")
    desktop = _FakeDesktopAdapter()
    runner = ComputerUseRunner(
        config=config,
        root_dir=root_dir,
        adapters=RuntimeAdapters(
            browser=_FakeBrowserAdapter(desktop=desktop),
            desktop=desktop,
            dialog=FileDialogAdapter(allowed_roots=[tmp_path]),
        ),
    )

    payload = runner.run(
        prompt=(
            'open "https://ops.example.internal/queue"\n'
            f'upload "{outside_path}" to "#upload"'
        ),
        job_id="job-runtime-upload-outside-root",
        mode=ComputerUseMode.EXECUTE,
    )

    assert payload["job"]["status"] == "failed"
    status_payload = json.loads(
        (root_dir / "job-runtime-upload-outside-root" / "status.json").read_text(
            encoding="utf-8"
        )
    )
    assert status_payload["computer_use"]["file_operation_mismatch"]["code"] == (
        "path_outside_allowed_roots"
    )
    assert status_payload["computer_use"]["last_verification_result"]["mismatch_code"] == (
        "path_outside_allowed_roots"
    )


def test_computer_use_runner_fails_closed_on_missing_upload_file(tmp_path: Path) -> None:
    root_dir = tmp_path / "jobs"
    missing_path = tmp_path / "missing-upload.txt"
    config = RuntimeConfig.from_profile("default")
    desktop = _FakeDesktopAdapter()
    runner = ComputerUseRunner(
        config=config,
        root_dir=root_dir,
        adapters=RuntimeAdapters(
            browser=_FakeBrowserAdapter(desktop=desktop),
            desktop=desktop,
            dialog=FileDialogAdapter(allowed_roots=[tmp_path]),
        ),
    )

    payload = runner.run(
        prompt=(
            'open "https://ops.example.internal/queue"\n'
            f'upload "{missing_path}" to "#upload"'
        ),
        job_id="job-runtime-upload-missing",
        mode=ComputerUseMode.EXECUTE,
    )

    assert payload["job"]["status"] == "failed"
    status_payload = json.loads(
        (root_dir / "job-runtime-upload-missing" / "status.json").read_text(
            encoding="utf-8"
        )
    )
    assert status_payload["computer_use"]["file_operation_mismatch"]["code"] == "file_missing"


def test_computer_use_runner_verifies_download_artifact_and_indexes_it(tmp_path: Path) -> None:
    root_dir = tmp_path / "jobs"
    output_path = tmp_path / "artifact.txt"
    config = RuntimeConfig.from_profile("default")
    desktop = _FakeDesktopAdapter()
    runner = ComputerUseRunner(
        config=config,
        root_dir=root_dir,
        adapters=RuntimeAdapters(
            browser=_FakeBrowserAdapter(desktop=desktop),
            desktop=desktop,
            dialog=FileDialogAdapter(allowed_roots=[tmp_path]),
        ),
    )

    payload = runner.run(
        prompt=(
            'open "https://ops.example.internal/queue"\n'
            f'download "#download" to "{output_path}"'
        ),
        job_id="job-runtime-download-success",
        mode=ComputerUseMode.EXECUTE,
    )

    assert payload["job"]["status"] == "completed"
    assert output_path.exists()
    status_payload = json.loads(
        (root_dir / "job-runtime-download-success" / "status.json").read_text(
            encoding="utf-8"
        )
    )
    verification = status_payload["computer_use"]["last_verification_result"]
    assert verification["expected_file_operation"]["operation"] == "download"
    assert verification["observed_file_operation"]["file_size_bytes"] > 0
    assert status_payload["computer_use"]["artifacts"]["download_file"]["download_path"] == str(
        output_path
    )
    assert (
        str(output_path)
        in status_payload["computer_use"]["world_model"]["filesystem_result_set"]
    )


def test_computer_use_runner_fails_closed_when_download_artifact_is_not_created(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "jobs"
    output_path = tmp_path / "missing-artifact.txt"
    config = RuntimeConfig.from_profile("default")
    desktop = _FakeDesktopAdapter()
    runner = ComputerUseRunner(
        config=config,
        root_dir=root_dir,
        adapters=RuntimeAdapters(
            browser=_FakeBrowserAdapter(desktop=desktop, create_download_artifact=False),
            desktop=desktop,
            dialog=FileDialogAdapter(allowed_roots=[tmp_path]),
        ),
    )

    payload = runner.run(
        prompt=(
            'open "https://ops.example.internal/queue"\n'
            f'download "#download" to "{output_path}"'
        ),
        job_id="job-runtime-download-missing",
        mode=ComputerUseMode.EXECUTE,
    )

    assert payload["job"]["status"] == "failed"
    status_payload = json.loads(
        (root_dir / "job-runtime-download-missing" / "status.json").read_text(
            encoding="utf-8"
        )
    )
    assert status_payload["computer_use"]["file_operation_mismatch"]["code"] == (
        "file_not_created"
    )
    events = _read_events(root_dir / "job-runtime-download-missing" / "events.jsonl")
    mismatch_events = [
        event for event in events if event["event"] == "computer_use.file_operation_mismatch"
    ]
    assert len(mismatch_events) == 1
    assert mismatch_events[0]["data"]["reason_code"] == "file_not_created"


def test_computer_use_runner_honors_pause_and_resume(tmp_path: Path) -> None:
    root_dir = tmp_path / "jobs"
    job_id = "job-runtime-pause"
    config = RuntimeConfig.from_profile("default")
    desktop = _FakeDesktopAdapter()
    pause_triggered = {"value": False}

    def request_pause(action: ProposedAction) -> None:
        if action.action_id == "open_url" and not pause_triggered["value"]:
            SessionControlBus(root_dir / job_id).write(SessionCommand.PAUSE, reason="test_pause")
            pause_triggered["value"] = True

    runner = ComputerUseRunner(
        config=config,
        root_dir=root_dir,
        adapters=RuntimeAdapters(
            browser=_FakeBrowserAdapter(desktop=desktop, on_verified=request_pause),
            desktop=desktop,
            dialog=FileDialogAdapter(allowed_roots=[tmp_path]),
        ),
    )
    outcome: dict[str, object] = {}

    def worker() -> None:
        try:
            outcome["payload"] = runner.run(
                prompt=(
                    'open "https://ops.example.internal/queue"\n'
                    'type "Aegis Operator" into "#name"'
                ),
                job_id=job_id,
                mode=ComputerUseMode.EXECUTE,
            )
        except Exception as exc:  # noqa: BLE001
            outcome["error"] = exc

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    status_path = root_dir / job_id / "status.json"
    _wait_until(
        lambda: status_path.exists()
        and json.loads(status_path.read_text(encoding="utf-8"))["computer_use"]["paused"] is True
    )

    control_runner = ComputerUseRunner(config=config, root_dir=root_dir)
    control_runner.request_control(job_id=job_id, command=SessionCommand.RESUME)
    thread.join(timeout=5.0)

    assert not thread.is_alive()
    assert "error" not in outcome
    payload = outcome["payload"]
    assert isinstance(payload, dict)
    assert payload["job"]["status"] == "completed"
    event_names = _read_event_names(root_dir / job_id / "events.jsonl")
    assert "session_paused" in event_names
    assert "session_resumed" in event_names


def test_computer_use_runner_fails_closed_on_verification_mismatch(tmp_path: Path) -> None:
    root_dir = tmp_path / "jobs"
    config = RuntimeConfig.from_profile("default")
    desktop = _FakeDesktopAdapter()
    runner = ComputerUseRunner(
        config=config,
        root_dir=root_dir,
        adapters=RuntimeAdapters(
            browser=_FailingClickBrowserAdapter(desktop=desktop),
            desktop=desktop,
            dialog=FileDialogAdapter(allowed_roots=[tmp_path]),
        ),
    )

    payload = runner.run(
        prompt='open "https://ops.example.internal/queue"\nclick "#advance"',
        job_id="job-runtime-verify-fail",
        mode=ComputerUseMode.EXECUTE,
    )

    assert payload["job"]["status"] == "failed"
    status_payload = json.loads(
        (root_dir / "job-runtime-verify-fail" / "status.json").read_text(encoding="utf-8")
    )
    assert status_payload["computer_use"]["last_verification_result"]["mismatch_code"] == (
        "no_state_change_after_click"
    )
    event_names = _read_event_names(root_dir / "job-runtime-verify-fail" / "events.jsonl")
    assert "action_failed" in event_names


def test_computer_use_runner_honors_stop_while_paused(tmp_path: Path) -> None:
    root_dir = tmp_path / "jobs"
    job_id = "job-runtime-stop"
    config = RuntimeConfig.from_profile("default")
    desktop = _FakeDesktopAdapter()
    pause_triggered = {"value": False}

    def request_pause(action: ProposedAction) -> None:
        if action.action_id == "open_url" and not pause_triggered["value"]:
            SessionControlBus(root_dir / job_id).write(SessionCommand.PAUSE, reason="test_pause")
            pause_triggered["value"] = True

    runner = ComputerUseRunner(
        config=config,
        root_dir=root_dir,
        adapters=RuntimeAdapters(
            browser=_FakeBrowserAdapter(desktop=desktop, on_verified=request_pause),
            desktop=desktop,
            dialog=FileDialogAdapter(allowed_roots=[tmp_path]),
        ),
    )
    outcome: dict[str, object] = {}

    def worker() -> None:
        try:
            outcome["payload"] = runner.run(
                prompt=(
                    'open "https://ops.example.internal/queue"\n'
                    'type "Aegis Operator" into "#name"'
                ),
                job_id=job_id,
                mode=ComputerUseMode.EXECUTE,
            )
        except Exception as exc:  # noqa: BLE001
            outcome["error"] = exc

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    status_path = root_dir / job_id / "status.json"
    _wait_until(
        lambda: status_path.exists()
        and json.loads(status_path.read_text(encoding="utf-8"))["computer_use"]["paused"] is True
    )

    control_runner = ComputerUseRunner(config=config, root_dir=root_dir)
    control_runner.request_control(job_id=job_id, command=SessionCommand.STOP)
    thread.join(timeout=5.0)

    assert not thread.is_alive()
    assert "error" in outcome
    assert "session stopped by operator" in str(outcome["error"])

    status_payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert status_payload["computer_use"]["lifecycle_state"] == "stopped"
    assert status_payload["job"]["status"] == "failed"
    event_names = _read_event_names(root_dir / job_id / "events.jsonl")
    assert "session_stopped" in event_names


def test_computer_use_runner_pauses_at_pre_action_checkpoint_and_resumes(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "jobs"
    job_id = "job-runtime-pre-action-pause"
    config = RuntimeConfig.from_profile("default")
    desktop = _FakeDesktopAdapter()
    control_runner = ComputerUseRunner(config=config, root_dir=root_dir)
    first_pause: dict[str, object] = {}

    def request_pause(action: ProposedAction) -> None:
        if action.action_id == "open_url" and not first_pause:
            first_pause.update(
                control_runner.request_control(job_id=job_id, command=SessionCommand.PAUSE)
            )

    runner = ComputerUseRunner(
        config=config,
        root_dir=root_dir,
        adapters=RuntimeAdapters(
            browser=_FakeBrowserAdapter(desktop=desktop, on_verified=request_pause),
            desktop=desktop,
            dialog=FileDialogAdapter(allowed_roots=[tmp_path]),
        ),
    )
    outcome: dict[str, object] = {}

    def worker() -> None:
        try:
            outcome["payload"] = runner.run(
                prompt=(
                    'open "https://ops.example.internal/queue"\n'
                    'wait "0.5"\n'
                    'type "Aegis Operator" into "#name"'
                ),
                job_id=job_id,
                mode=ComputerUseMode.EXECUTE,
            )
        except Exception as exc:  # noqa: BLE001
            outcome["error"] = exc

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    status_path = root_dir / job_id / "status.json"
    _wait_until(
        lambda: status_path.exists() and bool(first_pause),
        timeout_s=10.0,
    )
    assert first_pause["outcome"] == "accepted"
    _wait_until(
        lambda: json.loads(status_path.read_text(encoding="utf-8"))["computer_use"][
            "session_state"
        ]
        == SessionExecutionState.PAUSED.value
    )

    paused_status = json.loads(status_path.read_text(encoding="utf-8"))
    assert paused_status["computer_use"]["last_safe_checkpoint"] == "after_verify"
    assert _read_event_names(root_dir / job_id / "events.jsonl").count("action_started") == 1

    duplicate_pause = control_runner.request_control(job_id=job_id, command=SessionCommand.PAUSE)
    assert duplicate_pause["outcome"] == "already_applied"

    resume_result = control_runner.request_control(job_id=job_id, command=SessionCommand.RESUME)
    assert resume_result["outcome"] == "accepted"
    thread.join(timeout=5.0)

    assert not thread.is_alive()
    assert "error" not in outcome
    payload = outcome["payload"]
    assert isinstance(payload, dict)
    assert payload["job"]["status"] == "completed"
    events = _read_event_names(root_dir / job_id / "events.jsonl")
    assert events.index("computer_use.control_command_received") < events.index(
        "computer_use.pause_requested"
    )
    assert events.index("computer_use.pause_requested") < events.index("computer_use.paused")
    assert events.index("computer_use.resume_requested") < events.index("computer_use.resumed")


def test_computer_use_runner_stops_at_safe_checkpoint_during_long_action(
    tmp_path: Path,
) -> None:
    root_dir = tmp_path / "jobs"
    job_id = "job-runtime-mid-run-stop"
    config = RuntimeConfig.from_profile("default")
    desktop = _FakeDesktopAdapter()
    runner = ComputerUseRunner(
        config=config,
        root_dir=root_dir,
        adapters=RuntimeAdapters(
            browser=_FakeBrowserAdapter(desktop=desktop, wait_delay_s=1.0),
            desktop=desktop,
            dialog=FileDialogAdapter(allowed_roots=[tmp_path]),
        ),
    )
    outcome: dict[str, object] = {}

    def worker() -> None:
        try:
            outcome["payload"] = runner.run(
                prompt=(
                    'open "https://ops.example.internal/queue"\n'
                    'wait "1.0"\n'
                    'type "Aegis Operator" into "#name"'
                ),
                job_id=job_id,
                mode=ComputerUseMode.EXECUTE,
            )
        except Exception as exc:  # noqa: BLE001
            outcome["error"] = exc

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    events_path = root_dir / job_id / "events.jsonl"
    _wait_until(
        lambda: events_path.exists()
        and _read_event_names(events_path).count("action_started") >= 2,
        timeout_s=10.0,
    )
    control_runner = ComputerUseRunner(config=config, root_dir=root_dir)
    stop_result = control_runner.request_control(job_id=job_id, command=SessionCommand.STOP)
    assert stop_result["outcome"] == "accepted"
    thread.join(timeout=10.0)

    assert not thread.is_alive()
    assert "error" in outcome
    assert "session stopped by operator" in str(outcome["error"])

    status_payload = json.loads(
        (root_dir / job_id / "status.json").read_text(encoding="utf-8")
    )
    assert status_payload["computer_use"]["session_state"] == SessionExecutionState.STOPPED.value
    assert status_payload["computer_use"]["stopped_by_user"] is True
    assert status_payload["computer_use"]["last_safe_checkpoint"] == "after_execute"
    event_names = _read_event_names(events_path)
    assert event_names.index("computer_use.control_command_received") < event_names.index(
        "computer_use.stop_requested"
    )
    assert event_names.index("computer_use.stop_requested") < event_names.index(
        "computer_use.stopped"
    )

    duplicate_stop = control_runner.request_control(job_id=job_id, command=SessionCommand.STOP)
    assert duplicate_stop["outcome"] == "already_applied"


def test_computer_use_runner_rejects_invalid_resume_while_running(tmp_path: Path) -> None:
    root_dir = tmp_path / "jobs"
    job_id = "job-runtime-invalid-resume"
    config = RuntimeConfig.from_profile("default")
    desktop = _FakeDesktopAdapter()
    control_runner = ComputerUseRunner(config=config, root_dir=root_dir)
    resume_result: dict[str, object] = {}

    def request_invalid_resume(action: ProposedAction) -> None:
        if action.action_id == "open_url" and not resume_result:
            resume_result.update(
                control_runner.request_control(job_id=job_id, command=SessionCommand.RESUME)
            )

    runner = ComputerUseRunner(
        config=config,
        root_dir=root_dir,
        adapters=RuntimeAdapters(
            browser=_FakeBrowserAdapter(
                desktop=desktop,
                on_verified=request_invalid_resume,
                wait_delay_s=0.4,
            ),
            desktop=desktop,
            dialog=FileDialogAdapter(allowed_roots=[tmp_path]),
        ),
    )
    outcome: dict[str, object] = {}

    def worker() -> None:
        try:
            outcome["payload"] = runner.run(
                prompt=(
                    'open "https://ops.example.internal/queue"\n'
                    'wait "0.4"\n'
                    'type "Aegis Operator" into "#name"'
                ),
                job_id=job_id,
                mode=ComputerUseMode.EXECUTE,
            )
        except Exception as exc:  # noqa: BLE001
            outcome["error"] = exc

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    thread.join(timeout=5.0)

    assert not thread.is_alive()
    assert "error" not in outcome
    assert resume_result["outcome"] == "rejected"
    events = _read_events(root_dir / job_id / "events.jsonl")
    names = [event["event"] for event in events]
    received_index = names.index("computer_use.control_command_received")
    rejected_index = names.index("computer_use.control_command_rejected")
    assert received_index < rejected_index
    rejected = events[rejected_index]["data"]["result"]
    assert rejected["reason"] == "resume_not_allowed_from_running"


def test_computer_use_runner_stops_while_awaiting_approval(tmp_path: Path) -> None:
    root_dir = tmp_path / "jobs"
    job_id = "job-runtime-approval-stop"
    config = RuntimeConfig.from_profile("default").model_copy(
        update={
            "governance": RuntimeConfig.from_profile("default").governance.model_copy(
                update={"approval_store_path": str(tmp_path / "approvals.sqlite3")}
            )
        }
    )
    desktop = _FakeDesktopAdapter()
    runner = ComputerUseRunner(
        config=config,
        root_dir=root_dir,
        adapters=RuntimeAdapters(
            browser=_FakeBrowserAdapter(desktop=desktop),
            desktop=desktop,
            dialog=FileDialogAdapter(allowed_roots=[tmp_path]),
        ),
    )
    outcome: dict[str, object] = {}

    def worker() -> None:
        try:
            outcome["payload"] = runner.run(
                prompt='open "https://ops.example.internal/queue"\nclick "#submit"',
                job_id=job_id,
                mode=ComputerUseMode.EXECUTE,
            )
        except Exception as exc:  # noqa: BLE001
            outcome["error"] = exc

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    status_path = root_dir / job_id / "status.json"
    _wait_until(
        lambda: status_path.exists()
        and json.loads(status_path.read_text(encoding="utf-8"))["computer_use"]["session_state"]
        == SessionExecutionState.AWAITING_APPROVAL.value
    )
    control_runner = ComputerUseRunner(config=config, root_dir=root_dir)
    stop_result = control_runner.request_control(job_id=job_id, command=SessionCommand.STOP)
    assert stop_result["outcome"] == "accepted"
    thread.join(timeout=5.0)

    assert not thread.is_alive()
    assert "error" in outcome
    status_payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert status_payload["computer_use"]["session_state"] == SessionExecutionState.STOPPED.value
    assert status_payload["computer_use"]["stopped_by_user"] is True


def test_computer_use_runner_loads_recovery_state_for_paused_session(tmp_path: Path) -> None:
    root_dir = tmp_path / "jobs"
    job_id = "job-runtime-recovery-paused"
    config = RuntimeConfig.from_profile("default")
    desktop = _FakeDesktopAdapter()
    control_runner = ComputerUseRunner(config=config, root_dir=root_dir)

    def request_pause(action: ProposedAction) -> None:
        if action.action_id == "open_url":
            control_runner.request_control(job_id=job_id, command=SessionCommand.PAUSE)

    runner = ComputerUseRunner(
        config=config,
        root_dir=root_dir,
        adapters=RuntimeAdapters(
            browser=_FakeBrowserAdapter(desktop=desktop, on_verified=request_pause),
            desktop=desktop,
            dialog=FileDialogAdapter(allowed_roots=[tmp_path]),
        ),
    )
    outcome: dict[str, object] = {}

    def worker() -> None:
        try:
            outcome["payload"] = runner.run(
                prompt=(
                    'open "https://ops.example.internal/queue"\n'
                    'wait "0.5"\n'
                    'type "Aegis Operator" into "#name"'
                ),
                job_id=job_id,
                mode=ComputerUseMode.EXECUTE,
            )
        except Exception as exc:  # noqa: BLE001
            outcome["error"] = exc

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    status_path = root_dir / job_id / "status.json"
    _wait_until(
        lambda: status_path.exists()
        and json.loads(status_path.read_text(encoding="utf-8"))["computer_use"][
            "session_state"
        ]
        == SessionExecutionState.PAUSED.value
        and (root_dir / job_id / "events.jsonl").exists(),
        timeout_s=10.0,
    )

    recovery = control_runner.load_recovery_state(job_id=job_id)
    assert recovery["recoverable_state"] == SessionExecutionState.PAUSED.value
    assert recovery["resume_allowed"] is True
    assert recovery["last_completed_action_index"] == 0

    event_names = _read_event_names(root_dir / job_id / "events.jsonl")
    assert "computer_use.recovery_loaded" in event_names

    control_runner.request_control(job_id=job_id, command=SessionCommand.RESUME)
    thread.join(timeout=5.0)
    assert not thread.is_alive()
    assert "error" not in outcome


def test_computer_use_runner_marks_active_recovery_as_not_resumable(tmp_path: Path) -> None:
    root_dir = tmp_path / "jobs"
    job_id = "job-runtime-recovery-running"
    config = RuntimeConfig.from_profile("default")
    desktop = _FakeDesktopAdapter()
    runner = ComputerUseRunner(
        config=config,
        root_dir=root_dir,
        adapters=RuntimeAdapters(
            browser=_FakeBrowserAdapter(desktop=desktop, wait_delay_s=0.4),
            desktop=desktop,
            dialog=FileDialogAdapter(allowed_roots=[tmp_path]),
        ),
    )
    outcome: dict[str, object] = {}

    def worker() -> None:
        try:
            outcome["payload"] = runner.run(
                prompt=(
                    'open "https://ops.example.internal/queue"\n'
                    'wait "0.4"\n'
                    'type "Aegis Operator" into "#name"'
                ),
                job_id=job_id,
                mode=ComputerUseMode.EXECUTE,
            )
        except Exception as exc:  # noqa: BLE001
            outcome["error"] = exc

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    events_path = root_dir / job_id / "events.jsonl"
    _wait_until(
        lambda: events_path.exists()
        and _read_event_names(events_path).count("action_started") >= 2,
        timeout_s=10.0,
    )
    control_runner = ComputerUseRunner(config=config, root_dir=root_dir)
    recovery = control_runner.load_recovery_state(job_id=job_id)
    assert recovery["recoverable_state"] == SessionExecutionState.RUNNING.value
    assert recovery["resume_allowed"] is False

    thread.join(timeout=5.0)
    assert not thread.is_alive()
    assert "error" not in outcome
    assert "computer_use.recovery_not_resumable" in _read_event_names(events_path)
