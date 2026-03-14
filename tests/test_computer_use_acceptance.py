from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from binliquid.computer_use import ComputerUseMode, ComputerUseRunner, SessionCommand
from binliquid.runtime.config import RuntimeConfig

REAL_COMPUTER_USE_ENABLED = os.getenv("AEGISOS_ENABLE_REAL_COMPUTER_USE_TESTS") == "1"


def _wait_for_event_count(
    events_path: Path,
    *,
    event_name: str,
    count: int,
    timeout_s: float = 20.0,
) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if events_path.exists():
            names = [
                json.loads(line)["event"]
                for line in events_path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            if sum(name == event_name for name in names) >= count:
                return
        time.sleep(0.2)
    raise AssertionError(f"timed out waiting for {count} {event_name!r} events")


def _wait_for_session_state(
    status_path: Path,
    *,
    session_state: str,
    timeout_s: float = 20.0,
) -> dict[str, object]:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        if status_path.exists():
            payload = json.loads(status_path.read_text(encoding="utf-8"))
            if payload["computer_use"]["session_state"] == session_state:
                return payload
        time.sleep(0.2)
    raise AssertionError(f"timed out waiting for session_state={session_state!r}")


def _write_upload_download_site(site_dir: Path) -> None:
    (site_dir / "artifact.txt").write_text("runtime acceptance download", encoding="utf-8")
    (site_dir / "index.html").write_text(
        """
<!doctype html>
<html lang="en">
  <body>
    <form>
      <label for="name">Name</label>
      <input id="name" type="text" />
      <label for="role">Role</label>
      <select id="role">
        <option value="">Pick one</option>
        <option value="operator">operator</option>
      </select>
      <label for="upload">Upload</label>
      <input id="upload" type="file" />
    </form>
    <a id="download" href="/artifact.txt" download="artifact.txt">Download artifact</a>
  </body>
</html>
""".strip(),
        encoding="utf-8",
    )


def _start_site_server(site_dir: Path) -> tuple[ThreadingHTTPServer, threading.Thread]:
    handler = partial(SimpleHTTPRequestHandler, directory=str(site_dir))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


@pytest.mark.skipif(
    sys.platform != "darwin" or not REAL_COMPUTER_USE_ENABLED,
    reason=(
        "Enable with AEGISOS_ENABLE_REAL_COMPUTER_USE_TESTS=1 on macOS "
        "with Safari automation permissions."
    ),
)
def test_real_safari_upload_acceptance(tmp_path: Path) -> None:
    site_dir = tmp_path / "site"
    site_dir.mkdir()
    root_dir = tmp_path / "jobs"
    root_dir.mkdir()
    upload_path = root_dir / "upload.txt"
    upload_path.write_text("runtime acceptance upload", encoding="utf-8")
    _write_upload_download_site(site_dir)
    server, thread = _start_site_server(site_dir)

    try:
        config = RuntimeConfig.from_profile("default")
        runner = ComputerUseRunner(config=config, root_dir=root_dir)
        payload = runner.run(
            prompt="\n".join(
                [
                    'launch "Safari"',
                    f'open "http://127.0.0.1:{server.server_port}/index.html"',
                    'type "Aegis Operator" into "#name"',
                    'select "operator" in "#role"',
                    f'upload "{upload_path}" to "#upload"',
                ]
            ),
            job_id="real-safari-upload-acceptance",
            mode=ComputerUseMode.EXECUTE,
        )

        assert payload["job"]["status"] == "completed"
        status_payload = json.loads(
            (root_dir / "real-safari-upload-acceptance" / "status.json").read_text(
                encoding="utf-8"
            )
        )
        assert (
            status_payload["computer_use"]["last_verification_result"]["expected_file_operation"][
                "operation"
            ]
            == "upload"
        )
        assert (
            status_payload["computer_use"]["artifacts"]["upload_file"]["selected_file"]
            == str(upload_path)
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5.0)


@pytest.mark.skipif(
    sys.platform != "darwin" or not REAL_COMPUTER_USE_ENABLED,
    reason=(
        "Enable with AEGISOS_ENABLE_REAL_COMPUTER_USE_TESTS=1 on macOS "
        "with Safari automation permissions."
    ),
)
def test_real_safari_surface_drift_acceptance(tmp_path: Path) -> None:
    site_dir = tmp_path / "surface-site"
    site_dir.mkdir()
    (site_dir / "index.html").write_text(
        """
<!doctype html>
<html lang="en">
  <body>
    <label for="name">Name</label>
    <input id="name" type="text" />
    <label for="notes">Notes</label>
    <input id="notes" type="text" />
  </body>
</html>
""".strip(),
        encoding="utf-8",
    )
    (site_dir / "other.html").write_text(
        """
<!doctype html>
<html lang="en">
  <body>
    <p>Drifted away from the expected surface.</p>
  </body>
</html>
""".strip(),
        encoding="utf-8",
    )

    handler = partial(SimpleHTTPRequestHandler, directory=str(site_dir))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        config = RuntimeConfig.from_profile("default")
        root_dir = tmp_path / "jobs"
        runner = ComputerUseRunner(config=config, root_dir=root_dir)
        outcome: dict[str, object] = {}
        job_id = "real-safari-surface-drift"

        def worker() -> None:
            try:
                outcome["payload"] = runner.run(
                    prompt="\n".join(
                        [
                            f'open "http://127.0.0.1:{server.server_port}/index.html"',
                            'type "Aegis Operator" into "#name"',
                            'wait "2.0"',
                            'type "This step should fail after drift" into "#notes"',
                        ]
                    ),
                    job_id=job_id,
                    mode=ComputerUseMode.EXECUTE,
                )
            except Exception as exc:  # noqa: BLE001
                outcome["error"] = exc

        worker_thread = threading.Thread(target=worker, daemon=True)
        worker_thread.start()

        events_path = root_dir / job_id / "events.jsonl"
        _wait_for_event_count(events_path, event_name="action_verified", count=2)
        drift_url = f"http://127.0.0.1:{server.server_port}/other.html"
        subprocess.run(
            [
                "osascript",
                "-e",
                'tell application "Safari" to set URL of current tab of front window '
                f'to "{drift_url}"',
            ],
            check=True,
            capture_output=True,
            text=True,
        )

        worker_thread.join(timeout=30.0)
        assert not worker_thread.is_alive()
        assert "error" not in outcome
        payload = outcome["payload"]
        assert isinstance(payload, dict)
        assert payload["job"]["status"] == "failed"

        status_payload = json.loads(
            (root_dir / job_id / "status.json").read_text(encoding="utf-8")
        )
        assert status_payload["computer_use"]["surface_mismatch"]["code"] == "wrong_tab"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5.0)


@pytest.mark.skipif(
    sys.platform != "darwin" or not REAL_COMPUTER_USE_ENABLED,
    reason=(
        "Enable with AEGISOS_ENABLE_REAL_COMPUTER_USE_TESTS=1 on macOS "
        "with Safari automation permissions."
    ),
)
def test_real_safari_download_acceptance(tmp_path: Path) -> None:
    site_dir = tmp_path / "download-site"
    site_dir.mkdir()
    root_dir = tmp_path / "jobs"
    root_dir.mkdir()
    download_target = root_dir / "downloaded-artifact.txt"
    _write_upload_download_site(site_dir)
    server, thread = _start_site_server(site_dir)

    try:
        config = RuntimeConfig.from_profile("default")
        runner = ComputerUseRunner(config=config, root_dir=root_dir)
        payload = runner.run(
            prompt="\n".join(
                [
                    'launch "Safari"',
                    f'open "http://127.0.0.1:{server.server_port}/index.html"',
                    f'download "#download" to "{download_target}"',
                ]
            ),
            job_id="real-safari-download-acceptance",
            mode=ComputerUseMode.EXECUTE,
        )

        assert payload["job"]["status"] == "completed"
        assert download_target.exists()
        assert download_target.read_text(encoding="utf-8") == "runtime acceptance download"
        status_payload = json.loads(
            (root_dir / "real-safari-download-acceptance" / "status.json").read_text(
                encoding="utf-8"
            )
        )
        assert (
            status_payload["computer_use"]["last_verification_result"]["expected_file_operation"][
                "operation"
            ]
            == "download"
        )
        assert (
            status_payload["computer_use"]["artifacts"]["download_file"]["download_path"]
            == str(download_target)
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5.0)


@pytest.mark.skipif(
    sys.platform != "darwin" or not REAL_COMPUTER_USE_ENABLED,
    reason=(
        "Enable with AEGISOS_ENABLE_REAL_COMPUTER_USE_TESTS=1 on macOS "
        "with Safari automation permissions."
    ),
)
def test_real_safari_pause_resume_acceptance(tmp_path: Path) -> None:
    site_dir = tmp_path / "pause-site"
    site_dir.mkdir()
    root_dir = tmp_path / "jobs"
    root_dir.mkdir()
    _write_upload_download_site(site_dir)
    server, server_thread = _start_site_server(site_dir)

    try:
        config = RuntimeConfig.from_profile("default")
        runner = ComputerUseRunner(config=config, root_dir=root_dir)
        outcome: dict[str, object] = {}
        job_id = "real-safari-pause-resume"

        def worker() -> None:
            try:
                outcome["payload"] = runner.run(
                    prompt="\n".join(
                        [
                            'launch "Safari"',
                            f'open "http://127.0.0.1:{server.server_port}/index.html"',
                            'type "Aegis Operator" into "#name"',
                            'wait "2.0"',
                            'type "Recovered after pause" into "#name"',
                        ]
                    ),
                    job_id=job_id,
                    mode=ComputerUseMode.EXECUTE,
                )
            except Exception as exc:  # noqa: BLE001
                outcome["error"] = exc

        worker_thread = threading.Thread(target=worker, daemon=True)
        worker_thread.start()

        events_path = root_dir / job_id / "events.jsonl"
        status_path = root_dir / job_id / "status.json"
        _wait_for_event_count(events_path, event_name="action_verified", count=2)
        control_runner = ComputerUseRunner(config=config, root_dir=root_dir)
        control_runner.request_control(job_id=job_id, command=SessionCommand.PAUSE)
        paused_payload = _wait_for_session_state(status_path, session_state="paused")
        assert paused_payload["computer_use"]["last_safe_checkpoint"] == "before_action"

        control_runner.request_control(job_id=job_id, command=SessionCommand.RESUME)
        worker_thread.join(timeout=30.0)
        assert not worker_thread.is_alive()
        assert "error" not in outcome
        payload = outcome["payload"]
        assert isinstance(payload, dict)
        assert payload["job"]["status"] == "completed"
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5.0)


@pytest.mark.skipif(
    sys.platform != "darwin" or not REAL_COMPUTER_USE_ENABLED,
    reason=(
        "Enable with AEGISOS_ENABLE_REAL_COMPUTER_USE_TESTS=1 on macOS "
        "with Safari automation permissions."
    ),
)
def test_real_safari_stop_acceptance(tmp_path: Path) -> None:
    site_dir = tmp_path / "stop-site"
    site_dir.mkdir()
    root_dir = tmp_path / "jobs"
    root_dir.mkdir()
    _write_upload_download_site(site_dir)
    server, server_thread = _start_site_server(site_dir)

    try:
        config = RuntimeConfig.from_profile("default")
        runner = ComputerUseRunner(config=config, root_dir=root_dir)
        outcome: dict[str, object] = {}
        job_id = "real-safari-stop"

        def worker() -> None:
            try:
                outcome["payload"] = runner.run(
                    prompt="\n".join(
                        [
                            'launch "Safari"',
                            f'open "http://127.0.0.1:{server.server_port}/index.html"',
                            'wait "3.0"',
                            'type "This step should not execute" into "#name"',
                        ]
                    ),
                    job_id=job_id,
                    mode=ComputerUseMode.EXECUTE,
                )
            except Exception as exc:  # noqa: BLE001
                outcome["error"] = exc

        worker_thread = threading.Thread(target=worker, daemon=True)
        worker_thread.start()

        events_path = root_dir / job_id / "events.jsonl"
        status_path = root_dir / job_id / "status.json"
        _wait_for_event_count(events_path, event_name="action_started", count=2)
        control_runner = ComputerUseRunner(config=config, root_dir=root_dir)
        control_runner.request_control(job_id=job_id, command=SessionCommand.STOP)
        worker_thread.join(timeout=30.0)
        assert not worker_thread.is_alive()
        assert "error" in outcome
        status_payload = json.loads(status_path.read_text(encoding="utf-8"))
        assert status_payload["computer_use"]["session_state"] == "stopped"
        assert status_payload["computer_use"]["stopped_by_user"] is True
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5.0)
