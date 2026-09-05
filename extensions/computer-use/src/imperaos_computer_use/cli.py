from __future__ import annotations

import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import typer

from imperaos.cli import (
    _build_cli_overrides,
    _read_string,
    _record,
    _require_permission_or_exit,
    _with_contract_version,
)
from imperaos.contracts.version import OPERATOR_PANEL_CONTRACT_VERSION
from imperaos.runtime.config import RuntimeConfig, resolve_runtime_config
from imperaos.runtime.platform import PlatformInfo, current_platform
from imperaos_computer_use import ComputerUseMode
from imperaos_computer_use.runtime import ComputerUseRunner, SessionCommand
from imperaos_computer_use.vision_runtime.capability_resolver import (
    resolve_capability_decision_snapshot,
)
from imperaos_computer_use.vision_runtime.drivers.macos import MacOSVisionReadiness
from imperaos_computer_use.vision_runtime.platforms import build_platform_capabilities
from imperaos_computer_use.vision_runtime.provider_doctor import doctor_vision_provider
from imperaos_computer_use.vision_runtime.qualification import (
    missing_platform_qualification_result,
    run_macos_live_qualification,
    run_vision_qualification,
    validate_platform_qualification_report,
)
from imperaos_computer_use.vision_runtime.replay import (
    load_replay_summary,
    verify_qualification_report_replay,
    verify_replay,
)

app = typer.Typer(
    help="Paused, opt-in computer-use research extension. Live execution requires qualification."
)
computer_use_app = app
computer_use_vision_app = typer.Typer(help="Vision-first computer use commands")
computer_use_qualification_app = typer.Typer(help="Computer-use qualification commands")
computer_use_provider_app = typer.Typer(help="Computer-use provider readiness commands")
app.add_typer(computer_use_vision_app, name="vision")
app.add_typer(computer_use_qualification_app, name="qualification")
app.add_typer(computer_use_provider_app, name="provider")


def _current_git_sha() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def _load_json_file_if_present(path_value: str | None) -> dict[str, Any] | None:
    if not path_value:
        return None
    path = Path(path_value)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return payload if isinstance(payload, dict) else None


def _computer_use_evidence_payloads(
    computer_use_config: Any,
) -> tuple[dict[str, object], dict[str, str]]:
    evidence_by_platform: dict[str, object] = {}
    evidence_paths: dict[str, str] = {}
    macos_path_value = getattr(computer_use_config, "macos_qualification_report", "")
    macos_payload = _load_json_file_if_present(macos_path_value)
    if macos_payload is not None:
        evidence_by_platform["macos"] = macos_payload
        evidence_paths["macos"] = str(Path(macos_path_value))
    return evidence_by_platform, evidence_paths


def _computer_use_capability_snapshot(
    computer_use_config: Any,
    *,
    profile: str,
    current_platform_label: str,
    current_commit: str,
) -> dict[str, object]:
    evidence_by_platform, evidence_paths = _computer_use_evidence_payloads(computer_use_config)
    return resolve_capability_decision_snapshot(
        config=computer_use_config,
        profile=profile,
        current_platform=current_platform_label,
        current_commit=current_commit,
        evidence_by_platform=evidence_by_platform,
        evidence_paths=evidence_paths,
    )


def _filter_capability_snapshot(
    snapshot: dict[str, object],
    *,
    selected: str,
) -> dict[str, object]:
    if selected == "all":
        return snapshot
    platforms = snapshot.get("platforms")
    if not isinstance(platforms, dict) or selected not in platforms:
        return snapshot
    return {
        **snapshot,
        "status": platforms[selected].get("status")
        if isinstance(platforms[selected], dict)
        else snapshot.get("status"),
        "platforms": {selected: platforms[selected]},
    }


def _selected_capability_decision(
    snapshot: dict[str, object],
    *,
    selected: str,
    fallback_platform: str | None = None,
) -> dict[str, object]:
    platforms = snapshot.get("platforms")
    if not isinstance(platforms, dict) or not platforms:
        return {}
    platform_key = selected if selected != "all" else snapshot.get("currentPlatform")
    if (
        selected == "all"
        and isinstance(fallback_platform, str)
        and platform_key not in platforms
        and fallback_platform in platforms
    ):
        platform_key = fallback_platform
    if not isinstance(platform_key, str) or platform_key not in platforms:
        platform_key = "windows" if "windows" in platforms else next(iter(platforms))
    decision = platforms.get(platform_key, {})
    return decision if isinstance(decision, dict) else {}


def _operator_computer_use_capability_resolution(
    computer_use_config: Any,
    *,
    profile: str,
    platform_label: str,
    current_commit: str,
) -> dict[str, Any]:
    snapshot = _computer_use_capability_snapshot(
        computer_use_config,
        profile=profile,
        current_platform_label=platform_label,
        current_commit=current_commit,
    )
    decision = _selected_capability_decision(snapshot, selected=platform_label)
    platform = _read_string(decision, "platform", platform_label)
    evidence = _record(decision.get("evidence"))
    config = _record(decision.get("config"))
    driver = _record(decision.get("driverReadiness"))
    return {
        "schemaVersion": 1,
        "platform": platform if platform in {"macos", "windows", "linux"} else "unknown",
        "profile": profile,
        "status": _read_string(decision, "status", "blocked"),
        "liveEnabled": False,
        "supervisedLiveAllowed": decision.get("supervisedLiveAllowed") is True,
        "publicLiveClaimAllowed": False,
        "reasonCode": _read_string(
            decision,
            "reasonCode",
            "COMPUTER_USE_PLATFORM_NOT_QUALIFIED",
        ),
        "blockers": _operator_blocker_codes(decision),
        "evidence": {
            "status": _read_string(evidence, "status", "missing"),
            "source": _operator_evidence_source(evidence),
            "fresh": _read_string(evidence, "status", "missing") == "valid",
            "commitMatch": decision.get("supervisedLiveAllowed") is True,
            "configMatch": False,
            "providerMatch": decision.get("supervisedLiveAllowed") is True,
            "backendMatch": decision.get("supervisedLiveAllowed") is True,
        },
        "config": {
            "visionEnabled": config.get("visionEnabled") is True,
            "provider": _read_string(config, "visionProvider", "none"),
            "captureBackend": _read_string(config, "captureBackend", "disabled"),
            "inputBackend": _read_string(config, "inputBackend", "disabled"),
            "rawScreenshotPersistence": config.get("rawScreenshotPersistence") is True,
            "terminalPolicy": getattr(computer_use_config, "terminal_control", "deny"),
        },
        "driver": {
            "ready": (
                driver.get("captureReady") is True
                and driver.get("inputReady") is True
                and driver.get("permissionsReady") is True
            ),
            "captureReady": driver.get("captureReady") is True,
            "inputReady": driver.get("inputReady") is True,
            "permissionReady": driver.get("permissionsReady") is True,
        },
        "safety": {
            "failClosed": True,
            "rawScreenshotPersistenceAllowed": False,
            "requiresStepApproval": getattr(
                computer_use_config,
                "macos_require_step_approval",
                True,
            ),
            "sensitiveSurfaceStopEnabled": (
                getattr(computer_use_config, "sensitive_surface_policy", "stop") == "stop"
            ),
        },
    }


def _operator_blocker_codes(decision: dict[str, object]) -> list[str]:
    blockers = decision.get("blockers", [])
    if not isinstance(blockers, list):
        return []
    result: list[str] = []
    for blocker in blockers:
        if isinstance(blocker, dict):
            code = blocker.get("code")
            if isinstance(code, str):
                result.append(code)
        elif isinstance(blocker, str):
            result.append(blocker)
    return result


def _operator_evidence_source(evidence: dict[str, object]) -> str:
    path_value = evidence.get("path")
    if not isinstance(path_value, str) or not path_value:
        return "none"
    lowered = path_value.replace("\\", "/").lower()
    if "/fixtures/" in lowered or lowered.endswith("_fixture.json"):
        return "fixture"
    if "artifacts/" in lowered:
        return "default_path"
    return "explicit_path"


def _parse_computer_use_mode(mode: str) -> ComputerUseMode:
    normalized = mode.strip().lower()
    aliases = {
        "assisted": ComputerUseMode.STEP_APPROVAL,
        "step_approval": ComputerUseMode.STEP_APPROVAL,
        "step-approval": ComputerUseMode.STEP_APPROVAL,
        "supervised": ComputerUseMode.EXECUTE,
        "execute": ComputerUseMode.EXECUTE,
        "dry_run": ComputerUseMode.DRY_RUN,
        "dry-run": ComputerUseMode.DRY_RUN,
    }
    if normalized not in aliases:
        raise ValueError(f"unsupported computer use mode: {mode}")
    return aliases[normalized]


def _parse_computer_use_runtime(runtime: str) -> str:
    normalized = runtime.strip().lower().replace("_", "-")
    aliases = {
        "legacy-pilot": "legacy_pilot",
        "legacy": "legacy_pilot",
        "vision-first": "vision_first",
        "vision": "vision_first",
        "auto": "auto",
    }
    if normalized not in aliases:
        raise ValueError(f"unsupported computer use runtime: {runtime}")
    return aliases[normalized]


def _computer_use_vision_runtime_payload(
    vision_config: Any,
    *,
    profile: str,
    platform_label: str,
    current_commit: str,
) -> dict[str, Any]:
    qualification_reports = {}
    macos_report = _load_json_file_if_present(vision_config.macos_qualification_report)
    if macos_report is not None:
        qualification_reports["macos"] = macos_report
    platform_capabilities = build_platform_capabilities(
        vision_config,
        qualification_reports=qualification_reports,
        commit=current_commit,
    )
    current_label = platform_label if platform_label in platform_capabilities else "macos"
    current_capability = platform_capabilities[current_label]
    provider_configured = vision_config.vision_provider == "mock" or bool(
        vision_config.vision_provider != "none" and vision_config.vision_model
    )
    return {
        "enabled": current_capability.live_enabled,
        "stage": current_capability.stage,
        "platform": platform_label if platform_label in platform_capabilities else "unknown",
        "scope": "vision_first_desktop_web_file",
        "executionModes": current_capability.execution_modes,
        "replayable": True,
        "failClosed": True,
        "reasonCode": current_capability.reason_code,
        "summary": current_capability.summary,
        "provider": {
            "kind": vision_config.vision_provider,
            "name": vision_config.vision_provider,
            "configured": provider_configured,
            "model": vision_config.vision_model,
            "strictJson": True,
        },
        "safety": {
            "rawScreenshotPersistence": vision_config.raw_screenshot_persistence,
            "rawScreenshotRetention": vision_config.raw_screenshot_retention,
            "rawScreenshotMaxCount": vision_config.raw_screenshot_max_count,
            "terminalControl": vision_config.terminal_control,
            "sensitiveSurfacePolicy": vision_config.sensitive_surface_policy,
            "approvalRequiredForRiskyActions": True,
            "sensitiveSurfaceBlocked": True,
            "approvalFreshnessEnforced": True,
            "replayIntegrityVerified": True,
        },
        "platforms": {
            key: capability.model_dump(mode="json", by_alias=True)
            for key, capability in platform_capabilities.items()
        },
        "capabilityResolution": _operator_computer_use_capability_resolution(
            vision_config,
            profile=profile,
            platform_label=platform_label,
            current_commit=current_commit,
        ),
    }


@computer_use_vision_app.command("doctor")
def computer_use_vision_doctor(
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    platform: str = typer.Option(
        "macos",
        "--platform",
        help="Platform to inspect: macos|windows|linux",
    ),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    config, _source_map = resolve_runtime_config(profile=profile, root_dir=Path.cwd())
    normalized_platform = platform.strip().lower()
    if normalized_platform not in {"macos", "windows", "linux"}:
        raise typer.BadParameter("platform must be macos, windows, or linux")
    platform_info = current_platform()
    if normalized_platform != platform_info.label:
        platform_info = PlatformInfo(
            system=platform_info.system,
            label=normalized_platform,
            machine=platform_info.machine,
            release=platform_info.release,
        )
    qualification_report = _load_json_file_if_present(
        config.computer_use.macos_qualification_report
    )
    report = MacOSVisionReadiness(config.computer_use).evaluate(
        platform_info=platform_info,
        environment=dict(os.environ),
        qualification_report=qualification_report,
        commit=_current_git_sha(),
    )
    payload = _with_contract_version(report)
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(payload["stage"])


@computer_use_app.command("doctor")
def computer_use_doctor(
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    platform: str = typer.Option(
        "all",
        "--platform",
        help="Platform to inspect: all|macos|windows|linux",
    ),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    config, _source_map = resolve_runtime_config(profile=profile, root_dir=Path.cwd())
    current_commit = _current_git_sha()
    qualification_reports = {}
    macos_report = _load_json_file_if_present(config.computer_use.macos_qualification_report)
    if macos_report is not None:
        qualification_reports["macos"] = macos_report
    capabilities = build_platform_capabilities(
        config.computer_use,
        qualification_reports=qualification_reports,
        commit=current_commit,
    )
    selected = platform.strip().lower()
    if selected != "all":
        if selected not in capabilities:
            raise typer.BadParameter("platform must be all, macos, windows, or linux")
        capabilities = {selected: capabilities[selected]}
    actual_platform_label = current_platform().label
    capability_snapshot_platform = selected if selected != "all" else "unknown"
    capability_snapshot = _filter_capability_snapshot(
        _computer_use_capability_snapshot(
            config.computer_use,
            profile=profile,
            current_platform_label=capability_snapshot_platform,
            current_commit=current_commit,
        ),
        selected=selected,
    )
    base_payload: dict[str, Any] = {
        "runtime": "computer_use_vision",
        "profile": profile,
        "currentPlatform": current_platform().label,
        "platforms": {
            key: capability.model_dump(mode="json", by_alias=True)
            for key, capability in capabilities.items()
        },
        "capabilityResolution": capability_snapshot,
        "computerUse": {
            "visionRuntime": {
                "capability": _selected_capability_decision(
                    capability_snapshot,
                    selected=selected,
                    fallback_platform=actual_platform_label,
                )
            }
        },
    }
    if selected == "macos":
        base_payload.update(
            MacOSVisionReadiness(config.computer_use).evaluate(
                platform_info=PlatformInfo(
                    system=current_platform().system,
                    label="macos",
                    machine=current_platform().machine,
                    release=current_platform().release,
                ),
                environment=dict(os.environ),
                qualification_report=macos_report,
                commit=current_commit,
            )
        )
    payload = _with_contract_version(base_payload)
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"platforms={','.join(payload['platforms'])}")


@computer_use_app.command("summary")
def computer_use_summary(
    root_dir: str | None = typer.Option(None, "--root-dir", help="Artifact root"),
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    limit: int = typer.Option(20, "--limit", help="Recent run window"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    config = RuntimeConfig.from_profile(profile)
    bounded_limit = max(1, min(limit, 200))
    runner = ComputerUseRunner(config=config, root_dir=root_dir or config.team.artifact_dir)
    payload = {
        "contractVersion": OPERATOR_PANEL_CONTRACT_VERSION,
        **runner.summary(limit=bounded_limit),
    }
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(str(payload.get("summary") or ""))


@computer_use_provider_app.command("doctor")
def computer_use_provider_doctor(
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    provider: str = typer.Option("ollama", "--provider", help="Local provider to inspect"),
    model: str | None = typer.Option(None, "--model", help="Configured local vision model"),
    synthetic_fixture: bool = typer.Option(
        False,
        "--synthetic-fixture/--no-synthetic-fixture",
        help="Use a synthetic non-sensitive fixture image; required for readiness.",
    ),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    config, _source_map = resolve_runtime_config(profile=profile, root_dir=Path.cwd())
    selected_model = model or config.computer_use.vision_model
    payload = doctor_vision_provider(
        provider=provider,
        model=selected_model,
        synthetic_fixture=synthetic_fixture,
        timeout_s=config.computer_use.vision_provider_timeout_s,
        max_retries=config.computer_use.vision_provider_max_retries,
        environment=os.environ,
    )
    payload = _with_contract_version(payload)
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(str(payload.get("status")))


@computer_use_qualification_app.command("run")
def computer_use_qualification_run(
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    platform: str = typer.Option("macos", "--platform", help="macos"),
    suite: str = typer.Option("live-fixture-smoke", "--suite", help="Qualification suite"),
    mode: str = typer.Option("supervised", "--mode", help="preflight|supervised"),
    provider: str | None = typer.Option(None, "--provider", help="Override vision provider"),
    model: str | None = typer.Option(None, "--model", help="Override vision model"),
    output: str = typer.Option(
        "artifacts/computer_use/macos_qualification_report.json",
        "--output",
        help="Qualification report output path",
    ),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    normalized_platform = platform.strip().lower()
    if normalized_platform != "macos":
        payload = _with_contract_version(
            {
                "schemaVersion": "1.0",
                "platform": normalized_platform,
                "status": "blocked",
                "stage": "not_qualified",
                "reasonCode": f"{normalized_platform.upper()}_COMPUTER_USE_NOT_QUALIFIED",
                "blockers": [f"{normalized_platform.upper()}_COMPUTER_USE_NOT_QUALIFIED"],
            }
        )
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    if mode.strip().lower() not in {"preflight", "supervised"}:
        raise typer.BadParameter("mode must be preflight or supervised for macOS qualification")
    config, _source_map = resolve_runtime_config(profile=profile, root_dir=Path.cwd())
    computer_use_config = config.computer_use
    if provider is not None or model is not None:
        updates: dict[str, Any] = {}
        if provider is not None:
            updates["vision_provider"] = provider
        if model is not None:
            updates["vision_model"] = model
        computer_use_config = computer_use_config.model_copy(update=updates)
    report_payload = run_macos_live_qualification(
        config=computer_use_config,
        suite=suite,
        mode=mode,
        output_path=Path(output),
        env=os.environ,
    )
    payload = _with_contract_version(report_payload)
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(str(payload.get("status")))


@computer_use_qualification_app.command("verify")
def computer_use_qualification_verify(
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    platform: str | None = typer.Option(None, "--platform", help="macos|windows|linux"),
    report: str | None = typer.Option(None, "--report", help="Qualification report JSON path"),
    schema: str | None = typer.Option(
        None,
        "--schema",
        help="Qualification JSON schema path for fixture validation",
    ),
    input_path: str | None = typer.Option(
        None,
        "--input",
        help="Qualification fixture JSON path for static validation",
    ),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    if input_path is not None:
        payload = _verify_computer_use_qualification_fixture(
            schema_path=Path(schema) if schema else None,
            input_path=Path(input_path),
        )
        if json_output:
            typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            typer.echo(payload["status"])
        if payload["status"] != "pass":
            raise typer.Exit(code=1)
        return

    if platform is None or report is None:
        raise typer.BadParameter("provide either --schema/--input or --platform/--report")

    config, _source_map = resolve_runtime_config(profile=profile, root_dir=Path.cwd())
    normalized_platform = platform.strip().lower()
    report_path = Path(report)
    if report_path.exists():
        validation = validate_platform_qualification_report(
            json.loads(report_path.read_text(encoding="utf-8")),
            platform=normalized_platform,
            config=config.computer_use,
            commit=_current_git_sha(),
        )
    else:
        validation = missing_platform_qualification_result(normalized_platform)
    payload = validation.model_dump(mode="json")
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(validation.status)
    if not validation.allowed:
        raise typer.Exit(code=1)


def _verify_computer_use_qualification_fixture(
    *,
    schema_path: Path | None,
    input_path: Path,
) -> dict[str, Any]:
    blockers: list[str] = []
    if not input_path.exists():
        return {
            "status": "fail",
            "allowed": False,
            "blockers": ["VISION_PLATFORM_QUALIFICATION_MISSING"],
            "inputPath": str(input_path),
        }
    fixture = json.loads(input_path.read_text(encoding="utf-8"))
    if schema_path is not None:
        if not schema_path.exists():
            blockers.append("VISION_PLATFORM_QUALIFICATION_SCHEMA_MISSING")
        else:
            blockers.extend(_validate_json_schema(schema_path, fixture))

    fixture_platform = str(fixture.get("platform", "")).strip().lower()
    fixture_config = _fixture_runtime_config(fixture)
    validation = validate_platform_qualification_report(
        fixture,
        platform=fixture_platform,
        config=fixture_config,
        commit=str(fixture.get("commit", "")),
    )
    blockers.extend(validation.blockers)
    checks = _qualification_fixture_checks(fixture)
    blockers.extend(reason for reason, ok in checks.items() if not ok)

    return {
        "status": "pass" if not blockers else "fail",
        "allowed": False,
        "reviewOnly": True,
        "runtimeLiveEnabled": False,
        "schemaPath": str(schema_path) if schema_path else None,
        "inputPath": str(input_path),
        "platform": fixture_platform or None,
        "fixtureStatus": validation.status,
        "checks": checks,
        "blockers": blockers,
    }


def _validate_json_schema(schema_path: Path, fixture: dict[str, Any]) -> list[str]:
    try:
        import jsonschema
    except ModuleNotFoundError:
        return []
    schema_payload = json.loads(schema_path.read_text(encoding="utf-8"))
    try:
        jsonschema.Draft202012Validator(schema_payload).validate(fixture)
    except jsonschema.ValidationError as exc:
        return [f"VISION_PLATFORM_QUALIFICATION_SCHEMA_INVALID:{exc.json_path}"]
    return []


def _fixture_runtime_config(fixture: dict[str, Any]) -> Any:
    platform = str(fixture.get("platform", "")).strip().lower()
    provider = fixture.get("provider") if isinstance(fixture.get("provider"), dict) else {}
    backends = fixture.get("backends") if isinstance(fixture.get("backends"), dict) else {}
    updates: dict[str, Any] = {
        "vision_enabled": True,
        "vision_provider": str(provider.get("name") or "none"),
        "vision_model": str(provider.get("model") or "") or None,
    }
    if platform in {"macos", "windows", "linux"}:
        updates[f"{platform}_live_enabled"] = True
        updates[f"{platform}_capture_backend"] = str(backends.get("capture", "disabled"))
        updates[f"{platform}_input_backend"] = str(backends.get("input", "disabled"))
    return RuntimeConfig().computer_use.model_copy(update=updates)


def _qualification_fixture_checks(fixture: dict[str, Any]) -> dict[str, bool]:
    safety = fixture.get("safety") if isinstance(fixture.get("safety"), dict) else {}
    raw_count = safety.get(
        "rawScreenshotsPersisted",
        fixture.get("artifacts", {}).get("rawScreenshotCount", -1)
        if isinstance(fixture.get("artifacts"), dict)
        else -1,
    )
    return {
        "has_platform_identity": bool(fixture.get("platform")),
        "has_config_hash": bool(fixture.get("configHash")),
        "has_safety_invariants": bool(safety),
        "approval_freshness_enforced": safety.get("approvalFreshnessEnforced") is True,
        "replay_integrity_verified": (
            safety.get("replayIntegrityVerified") is True
            or safety.get("replayIntegrityEnforced") is True
        ),
        "raw_screenshots_not_persisted": int(raw_count) == 0,
        "has_evidence_placeholders": isinstance(fixture.get("evidence", []), list),
        "does_not_enable_live_runtime": True,
    }


@computer_use_app.command("replay")
def computer_use_replay(
    job_id: str | None = typer.Option(None, "--job-id", help="Vision computer-use job id"),
    report: str | None = typer.Option(
        None,
        "--report",
        help="macOS qualification report JSON path",
    ),
    root_dir: str | None = typer.Option(None, "--root-dir", help="Artifact root"),
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    verify: bool = typer.Option(False, "--verify/--no-verify", help="Verify replay integrity"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    if report is not None:
        payload = _with_contract_version(verify_qualification_report_replay(Path(report)))
        if json_output:
            typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            typer.echo(f"report={report} verified={payload.get('verified')}")
        if verify and not payload.get("verified"):
            raise typer.Exit(code=1)
        return
    if job_id is None:
        raise typer.BadParameter("provide --job-id or --report")
    config = RuntimeConfig.from_profile(profile)
    job_dir = Path(root_dir or config.team.artifact_dir) / job_id
    payload = load_replay_summary(job_dir)
    if verify:
        payload["verification"] = verify_replay(job_dir)
    payload = _with_contract_version(payload)
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"job_id={job_id} verified={payload.get('verified')}")


@computer_use_app.command("qualify")
def computer_use_qualify(
    runtime: str = typer.Option("vision-first", "--runtime", help="vision-first"),
    suite: str = typer.Option("smoke", "--suite", help="Qualification suite"),
    mode: str = typer.Option("deterministic", "--mode", help="deterministic|live"),
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    task_path: str = typer.Option(
        "benchmarks/tasks/computer_use_vision/smoke_tasks.jsonl",
        "--task-path",
        help="Qualification task JSONL path",
    ),
    output_root: str = typer.Option(
        "artifacts/computer_use_vision_qualification",
        "--output-root",
        help="Qualification output root",
    ),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    if _parse_computer_use_runtime(runtime) != "vision_first":
        payload = _with_contract_version(
            {
                "artifact_version": "computer_use_vision_qualification/v1",
                "status": "blocked",
                "blocking_reasons": ["UNSUPPORTED_RUNTIME"],
            }
        )
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        raise typer.Exit(code=1)
    config, _source_map = resolve_runtime_config(profile=profile, root_dir=Path.cwd())
    payload = run_vision_qualification(
        config=config.computer_use,
        mode=mode,
        suite=suite,
        task_path=Path(task_path),
        output_root=Path(output_root),
    )
    payload = _with_contract_version(payload)
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(payload["status"])


@computer_use_app.command("run")
def computer_use_run(
    once: str = typer.Option(..., "--once", help="Computer-use request"),
    job_id: str | None = typer.Option(None, "--job-id", help="Explicit job id"),
    case_id: str | None = typer.Option(None, "--case-id", help="Optional case id"),
    root_dir: str | None = typer.Option(None, "--root-dir", help="Artifact root"),
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    mode: str = typer.Option("supervised", "--mode", help="assisted|supervised|dry-run"),
    runtime: str = typer.Option(
        "legacy-pilot",
        "--runtime",
        help="legacy-pilot|vision-first|auto",
    ),
    max_steps: int | None = typer.Option(None, "--max-steps", help="Vision runtime step budget"),
    raw_screenshots: bool = typer.Option(
        False,
        "--raw-screenshots/--no-raw-screenshots",
        help="Persist raw screenshots only when explicitly enabled by config and request.",
    ),
    provider: str | None = typer.Option(None, help="Override provider"),
    fallback_provider: str | None = typer.Option(None, help="Override fallback provider"),
    model: str | None = typer.Option(None, "--model", help="Override model"),
    hf_model_id: str | None = typer.Option(None, "--hf-model-id", help="Override HF model id"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    resolved_mode = _parse_computer_use_mode(mode)
    config, _source_map = resolve_runtime_config(
        profile=profile,
        root_dir=Path.cwd(),
        cli_overrides=_build_cli_overrides(
            provider=provider,
            fallback_provider=fallback_provider,
            model=model,
            hf_model_id=hf_model_id,
        ),
    )
    _require_permission_or_exit(config, "runtime.run")
    effective_root = root_dir or config.team.artifact_dir
    effective_job_id = job_id or f"cu-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
    runner = ComputerUseRunner(config=config, root_dir=effective_root)
    try:
        payload = runner.run(
            prompt=once,
            job_id=effective_job_id,
            case_id=case_id,
            mode=resolved_mode,
            runtime_mode=_parse_computer_use_runtime(runtime),
            max_steps=max_steps,
            raw_screenshots=raw_screenshots,
        )
    except Exception as exc:  # noqa: BLE001
        payload = _with_contract_version(
            {
                "status": "error",
                "job_id": effective_job_id,
                "root_dir": effective_root,
                "error": str(exc),
            }
        )
        if json_output:
            typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            typer.echo(str(exc))
        raise typer.Exit(code=1) from None

    computer_use_payload = payload.get("computer_use", {})
    runtime_preflight = (
        computer_use_payload.get("runtimePreflight")
        if isinstance(computer_use_payload, dict)
        else None
    )
    job_status = str(payload.get("job", {}).get("status", "unknown"))
    blocked_by_preflight = job_status == "blocked" and isinstance(runtime_preflight, dict)
    output = _with_contract_version(
        {
            "status": "ok",
            "job_id": effective_job_id,
            "root_dir": "[redacted]" if blocked_by_preflight else effective_root,
            **payload,
        }
    )
    if json_output:
        typer.echo(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"job_id={effective_job_id} status={job_status}")
        if blocked_by_preflight:
            typer.echo(f"reason_code={runtime_preflight.get('reasonCode', 'UNKNOWN')}")
            typer.echo("hint=Run: imperaos computer-use doctor --json")


@computer_use_app.command("pause")
def computer_use_pause(
    job_id: str = typer.Option(..., "--job-id", help="Session job id"),
    root_dir: str | None = typer.Option(None, "--root-dir", help="Artifact root"),
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    config = RuntimeConfig.from_profile(profile)
    runner = ComputerUseRunner(config=config, root_dir=root_dir or config.team.artifact_dir)
    payload = _with_contract_version(
        runner.request_control(job_id=job_id, command=SessionCommand.PAUSE)
    )
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"job_id={job_id} requested=pause")


@computer_use_app.command("resume")
def computer_use_resume(
    job_id: str = typer.Option(..., "--job-id", help="Session job id"),
    root_dir: str | None = typer.Option(None, "--root-dir", help="Artifact root"),
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    config = RuntimeConfig.from_profile(profile)
    runner = ComputerUseRunner(config=config, root_dir=root_dir or config.team.artifact_dir)
    try:
        payload = _with_contract_version(
            runner.request_control(job_id=job_id, command=SessionCommand.RESUME)
        )
    except Exception as exc:  # noqa: BLE001
        typer.echo(
            json.dumps(
                _with_contract_version({"status": "error", "job_id": job_id, "error": str(exc)}),
                ensure_ascii=False,
                indent=2,
            )
        )
        raise typer.Exit(code=1) from None
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"job_id={job_id} requested=resume")


@computer_use_app.command("stop")
def computer_use_stop(
    job_id: str = typer.Option(..., "--job-id", help="Session job id"),
    root_dir: str | None = typer.Option(None, "--root-dir", help="Artifact root"),
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    config = RuntimeConfig.from_profile(profile)
    runner = ComputerUseRunner(config=config, root_dir=root_dir or config.team.artifact_dir)
    payload = _with_contract_version(
        runner.request_control(job_id=job_id, command=SessionCommand.STOP)
    )
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(f"job_id={job_id} requested=stop")


@computer_use_app.command("state")
def computer_use_state(
    job_id: str = typer.Option(..., "--job-id", help="Session job id"),
    root_dir: str | None = typer.Option(None, "--root-dir", help="Artifact root"),
    profile: str = typer.Option("balanced", "--profile", help="Runtime profile"),
    json_output: bool = typer.Option(True, "--json/--no-json", help="Emit JSON output"),
) -> None:
    config = RuntimeConfig.from_profile(profile)
    runner = ComputerUseRunner(config=config, root_dir=root_dir or config.team.artifact_dir)
    payload = _with_contract_version(runner.session_state(job_id=job_id))
    if json_output:
        typer.echo(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        typer.echo(
            f"job_id={job_id} state={payload.get('computer_use', {}).get('lifecycle_state')}"
        )


if __name__ == "__main__":
    app()
