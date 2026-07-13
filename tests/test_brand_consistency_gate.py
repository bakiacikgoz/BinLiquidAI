from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPT = REPO_ROOT / "scripts" / "run_brand_consistency_gate.py"
SCHEMA = REPO_ROOT / "contracts" / "rebrand" / "brand_audit_report.schema.json"
GIT = shutil.which("git")


def _legacy(*parts: str) -> str:
    return "".join(parts)


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    assert GIT is not None, "git is required for the brand consistency gate tests"
    return subprocess.run(
        [GIT, "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )


def _tracked_repo(tmp_path: Path, files: dict[str, str | bytes]) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True)
    _git(repo, "init", "--quiet")
    _git(repo, "config", "user.email", "brand-gate@example.invalid")
    _git(repo, "config", "user.name", "Brand Gate Test")
    for relative_path, content in files.items():
        path = repo / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
    _git(repo, "add", ".")
    _git(repo, "commit", "--quiet", "-m", "fixture")
    return repo


def _run_gate(
    repo: Path,
    output_root: Path,
    *,
    mode: str,
    artifact_roots: tuple[Path, ...] = (),
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    assert GIT is not None, "git is required for the brand consistency gate tests"
    env["GIT_EXECUTABLE"] = GIT
    command = [
        sys.executable,
        str(SCRIPT),
        "--mode",
        mode,
        "--repo-root",
        str(repo),
        "--output-root",
        str(output_root),
        "--json",
    ]
    for artifact_root in artifact_roots:
        command.extend(("--artifact-root", str(artifact_root)))
    return subprocess.run(command, capture_output=True, text=True, env=env)


def _report(output_root: Path) -> dict[str, object]:
    return json.loads((output_root / "brand_audit_report.json").read_text(encoding="utf-8"))


def test_inventory_normalizes_and_scans_tracked_paths_text_and_binary(tmp_path: Path) -> None:
    first_brand = _legacy("bin", "liquid")
    second_brand = _legacy("aeg", "is", "os")
    repo = _tracked_repo(
        tmp_path,
        {
            f"docs/{first_brand[:3].upper()}-{first_brand[3:].upper()}-notes.txt": (
                f"safe first line\n{first_brand.swapcase()} runtime\n"
                "\uff21\uff25\uff27\uff29\uff33\uff2f\uff33 provider\n"
            ),
            "assets/logo.bin": b"\x89PNG\x00\x01brand-metadata",
            "ignored.txt": second_brand,
        },
    )
    _git(repo, "update-index", "--assume-unchanged", "ignored.txt")
    output_root = tmp_path / "inventory"

    result = _run_gate(repo, output_root, mode="inventory")

    assert result.returncode == 0, result.stderr
    report = _report(output_root)
    assert report["status"] == "fail"
    assert report["canonicalBrand"] == "ImperaOS"
    assert report["scannedFileCount"] == 3
    assert report["gitCommit"] == _git(repo, "rev-parse", "HEAD").stdout.strip()
    findings = report["findings"]
    assert isinstance(findings, list)
    assert any(item["kind"] == "path" and item["classification"] == "blocking" for item in findings)
    assert any(
        item["kind"] == "content"
        and item["line"] == 2
        and item["classification"] == "blocking"
        for item in findings
    )
    assert any(
        item["kind"] == "content" and item["line"] == 3 and item["token"] == second_brand
        for item in findings
    )
    binary = next(item for item in findings if item["kind"] == "binary_metadata")
    assert binary["classification"] == "manual_review"
    assert binary["line"] is None
    assert len(binary["sha256"]) == 64
    assert report["legacyContentMatchCount"] > 0
    assert report["legacyPathMatchCount"] > 0
    assert report["binaryMetadataMatchCount"] == 1
    assert report["builtArtifactMatchCount"] == 0
    assert (output_root / "BRAND_AUDIT_REPORT.md").is_file()
    assert json.loads(result.stdout) == report


def test_enforce_returns_one_only_for_blocking_findings(tmp_path: Path) -> None:
    forbidden = _legacy("bin", "_", "liquid")
    blocking_repo = _tracked_repo(tmp_path / "blocking", {"settings.txt": forbidden})
    blocking = _run_gate(blocking_repo, tmp_path / "blocking-report", mode="enforce")
    assert blocking.returncode == 1
    assert _report(tmp_path / "blocking-report")["status"] == "fail"

    binary_repo = _tracked_repo(tmp_path / "binary", {"image.bin": b"\x00\x01\x02"})
    manual_only = _run_gate(binary_repo, tmp_path / "binary-report", mode="enforce")
    assert manual_only.returncode == 0, manual_only.stderr
    manual_report = _report(tmp_path / "binary-report")
    assert manual_report["status"] == "pass"
    assert manual_report["binaryMetadataMatchCount"] == 1


def test_artifact_mode_scans_untracked_build_outputs(tmp_path: Path) -> None:
    repo = _tracked_repo(tmp_path, {"README.md": "ImperaOS"})
    artifact_root = tmp_path / "dist"
    artifact_root.mkdir()
    (artifact_root / "metadata.txt").write_text(
        f"Name: {_legacy('Bin', 'Liquid', 'AI')}",
        encoding="utf-8",
    )
    (artifact_root / "application.bin").write_bytes(b"\x00\x01\x02")
    (artifact_root / f"{_legacy('aeg', 'is')}-launcher.txt").write_text(
        "ImperaOS",
        encoding="utf-8",
    )
    output_root = tmp_path / "artifact-report"

    result = _run_gate(
        repo,
        output_root,
        mode="artifacts",
        artifact_roots=(artifact_root,),
    )

    assert result.returncode == 1
    report = _report(output_root)
    assert report["status"] == "fail"
    assert report["builtArtifactMatchCount"] == 3
    assert all(item["kind"] == "built_artifact" for item in report["findings"])
    assert {item["classification"] for item in report["findings"]} == {
        "blocking",
        "manual_review",
    }


def test_report_schema_is_strict_and_accepts_generated_report(tmp_path: Path) -> None:
    repo = _tracked_repo(tmp_path, {"README.md": "ImperaOS"})
    output_root = tmp_path / "report"
    result = _run_gate(repo, output_root, mode="inventory")
    assert result.returncode == 0, result.stderr

    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert schema["additionalProperties"] is False
    assert schema["$defs"]["finding"]["additionalProperties"] is False
    Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER).validate(
        _report(output_root)
    )


def test_scanner_source_does_not_embed_forbidden_tokens() -> None:
    forbidden_tokens = (
        _legacy("bin", "liquid"),
        _legacy("bin", " ", "liquid"),
        _legacy("bin", "-", "liquid"),
        _legacy("bin", "_", "liquid"),
        _legacy("bin", "liquid", "ai"),
        _legacy("aeg", "is"),
        _legacy("aeg", "is", "os"),
    )
    for source_path in (SCRIPT, Path(__file__)):
        source = source_path.read_text(encoding="utf-8").casefold()
        assert all(token not in source for token in forbidden_tokens), source_path
