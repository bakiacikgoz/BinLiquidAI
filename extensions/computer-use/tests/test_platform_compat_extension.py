from types import SimpleNamespace

from imperaos_computer_use.adapters import FileDialogAdapter, ScaffoldBrowserAdapter
from imperaos_computer_use.runtime import ComputerUseRunner, RuntimeAdapters

from imperaos.runtime.config import RuntimeConfig


class _NoopDesktop:
    def launch_app(self, app_name: str) -> None:
        del app_name

    def focus_window(self, app_name: str) -> None:
        del app_name

    def frontmost_app(self) -> str:
        return ""

    def bundle_id(self, app_name: str) -> str | None:
        del app_name
        return None

    def inspect_windows(self, app_name: str) -> list[object]:
        del app_name
        return []

    def detect_dialog(self, app_name: str) -> bool:
        del app_name
        return False

    def observe_surface(self, app_name: str | None = None):
        del app_name
        raise AssertionError("Windows fail-closed boundary should avoid live desktop calls")


def test_computer_use_readiness_is_fail_closed_on_windows(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "imperaos_computer_use.runtime.current_platform",
        lambda: SimpleNamespace(
            system="Windows",
            label="windows",
            machine="AMD64",
            release="11",
        ),
    )
    runner = ComputerUseRunner(
        config=RuntimeConfig.from_profile("default"),
        root_dir=tmp_path / "jobs",
        adapters=RuntimeAdapters(
            browser=ScaffoldBrowserAdapter(),
            desktop=_NoopDesktop(),
            dialog=FileDialogAdapter(allowed_roots=[tmp_path]),
            finder=None,
            editor=None,
        ),
    )

    report = runner.readiness_report()

    assert report["platform"] == "windows"
    assert report["status"] == "blocked"
    assert report["computer_use"]["live_execution"] is False
    assert report["computer_use"]["reason_code"] == "WINDOWS_COMPUTER_USE_NOT_QUALIFIED"


def test_computer_use_run_stops_before_live_adapters_on_windows(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(
        "imperaos_computer_use.runtime.current_platform",
        lambda: SimpleNamespace(
            system="Windows",
            label="windows",
            machine="AMD64",
            release="11",
        ),
    )
    runner = ComputerUseRunner(
        config=RuntimeConfig.from_profile("default"),
        root_dir=tmp_path / "jobs",
        adapters=RuntimeAdapters(
            browser=ScaffoldBrowserAdapter(),
            desktop=_NoopDesktop(),
            dialog=FileDialogAdapter(allowed_roots=[tmp_path]),
            finder=None,
            editor=None,
        ),
    )

    payload = runner.run(prompt="Open https://example.com", job_id="cu-win")

    assert payload["job"]["status"] == "failed"
    assert (
        payload["computer_use"]["platform_boundary"]["reason_code"]
        == "WINDOWS_COMPUTER_USE_NOT_QUALIFIED"
    )
