from __future__ import annotations

import json
import os
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from binliquid.local_product.artifact_sources import (
    ArtifactDiscoveryReport,
    ArtifactDiscoveryRequest,
    DownloadedArtifact,
    RemoteArtifact,
    RemoteArtifactSource,
    artifact_name_matches,
    normalize_report_path,
    utc_now,
)
from binliquid.local_product.evidence_bundle import sha256_file


def _redact_url(url: str | None) -> str | None:
    if not url:
        return None
    return url.split("?")[0]


def _target_from_name(name: str) -> str | None:
    for target in ("windows-x64", "linux-x64", "darwin-arm64", "darwin-x64"):
        if target in name:
            return target
    return None


def github_auth_available(auth_mode: str = "auto") -> bool:
    if auth_mode in {"auto", "token_env"} and os.environ.get("GITHUB_TOKEN"):
        return True
    if auth_mode in {"auto", "gh_cli"} and shutil.which("gh"):
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            shell=False,
        )
        return result.returncode == 0
    return False


class GitHubActionsArtifactAdapter:
    def discover(self, request: ArtifactDiscoveryRequest) -> ArtifactDiscoveryReport:
        source = request.source
        if source.source_type != "github_actions":
            return ArtifactDiscoveryReport(
                status="blocked",
                source=source,
                branch=request.branch,
                headSha=request.head_sha,
                reasonCodes=["UNSUPPORTED_ARTIFACT_SOURCE"],
            )
        if not github_auth_available(source.auth_mode):
            return ArtifactDiscoveryReport(
                status="conditional",
                source=source,
                branch=request.branch,
                headSha=request.head_sha,
                reasonCodes=["blocked_external_auth"],
                warnings=["GitHub artifact auth unavailable; use manual bundle import."],
            )
        if shutil.which("gh"):
            return self._discover_with_gh(request)
        return self._discover_with_rest(request)

    def _discover_with_gh(self, request: ArtifactDiscoveryRequest) -> ArtifactDiscoveryReport:
        source = request.source
        workflow = request.workflow or source.workflow
        workflow_args = ["--workflow", workflow] if workflow else []
        run_cmd = [
            "gh",
            "run",
            "list",
            "--repo",
            source.repo or "",
            "--branch",
            request.branch,
            "--commit",
            request.head_sha,
            "--json",
            "databaseId,headSha,conclusion,workflowName",
            "--limit",
            str(request.limit),
            *workflow_args,
        ]
        result = subprocess.run(
            run_cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=30,
            shell=False,
        )
        if result.returncode != 0:
            return ArtifactDiscoveryReport(
                status="conditional",
                source=source,
                branch=request.branch,
                headSha=request.head_sha,
                reasonCodes=["GITHUB_RUN_DISCOVERY_FAILED"],
                warnings=["GitHub run discovery failed; output redacted."],
            )
        runs = json.loads(result.stdout or "[]")
        artifacts: list[RemoteArtifact] = []
        for run in runs:
            if run.get("headSha") != request.head_sha or run.get("conclusion") != "success":
                continue
            artifact_cmd = [
                "gh",
                "api",
                f"repos/{source.repo}/actions/runs/{run['databaseId']}/artifacts",
            ]
            artifact_result = subprocess.run(
                artifact_cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
                shell=False,
            )
            if artifact_result.returncode != 0:
                continue
            artifacts.extend(
                _parse_github_artifacts(
                    source=source,
                    payload=json.loads(artifact_result.stdout or "{}"),
                    head_sha=request.head_sha,
                )
            )
        return ArtifactDiscoveryReport(
            status="pass" if artifacts else "conditional",
            source=source,
            branch=request.branch,
            headSha=request.head_sha,
            artifacts=artifacts,
            reasonCodes=[] if artifacts else ["NO_MATCHING_ARTIFACTS"],
        )

    def _discover_with_rest(self, request: ArtifactDiscoveryRequest) -> ArtifactDiscoveryReport:
        source = request.source
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            return ArtifactDiscoveryReport(
                status="conditional",
                source=source,
                branch=request.branch,
                headSha=request.head_sha,
                reasonCodes=["blocked_external_auth"],
            )
        url = (
            f"https://api.github.com/repos/{source.repo}/actions/artifacts"
            f"?per_page=100"
        )
        req = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
            return ArtifactDiscoveryReport(
                status="conditional",
                source=source,
                branch=request.branch,
                headSha=request.head_sha,
                reasonCodes=["GITHUB_ARTIFACT_DISCOVERY_FAILED"],
            )
        artifacts = _parse_github_artifacts(
            source=source,
            payload=payload,
            head_sha=request.head_sha,
        )
        return ArtifactDiscoveryReport(
            status="pass" if artifacts else "conditional",
            source=source,
            branch=request.branch,
            headSha=request.head_sha,
            artifacts=artifacts,
            reasonCodes=[] if artifacts else ["NO_MATCHING_ARTIFACTS"],
        )

    def download(self, artifact: RemoteArtifact, output_root: Path) -> DownloadedArtifact:
        if artifact.expired:
            raise ValueError("GITHUB_ARTIFACT_EXPIRED")
        output_root.mkdir(parents=True, exist_ok=True)
        destination = output_root / f"{artifact.artifact_id}.zip"
        url = artifact.metadata_redacted.get("archive_download_url")
        if shutil.which("gh") and artifact.metadata_redacted.get("api_path"):
            with destination.open("wb") as handle:
                result = subprocess.run(
                    ["gh", "api", str(artifact.metadata_redacted["api_path"])],
                    stdout=handle,
                    stderr=subprocess.PIPE,
                    text=False,
                    timeout=60,
                    shell=False,
                )
            if result.returncode != 0:
                raise ValueError("GITHUB_ARTIFACT_DOWNLOAD_FAILED")
        elif url and os.environ.get("GITHUB_TOKEN"):
            req = urllib.request.Request(
                str(url),
                headers={"Authorization": f"Bearer {os.environ['GITHUB_TOKEN']}"},
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as response:
                    destination.write_bytes(response.read())
            except (urllib.error.URLError, TimeoutError):
                raise ValueError("GITHUB_ARTIFACT_DOWNLOAD_FAILED") from None
        else:
            raise ValueError("GITHUB_ARTIFACT_AUTH_UNAVAILABLE")
        return DownloadedArtifact(
            artifactId=artifact.artifact_id,
            sourceId=artifact.source_id,
            target=artifact.target,
            headSha=artifact.head_sha,
            downloadedPath=normalize_report_path(destination),
            sha256=sha256_file(destination),
            downloadedAtUtc=utc_now(),
            metadataRedacted=artifact.metadata_redacted,
        )


def _parse_github_artifacts(
    *,
    source: RemoteArtifactSource,
    payload: dict[str, Any],
    head_sha: str,
) -> list[RemoteArtifact]:
    artifacts: list[RemoteArtifact] = []
    for item in payload.get("artifacts", []):
        name = str(item.get("name", ""))
        if not artifact_name_matches(name, source.artifact_pattern):
            continue
        artifacts.append(
            RemoteArtifact(
                artifactId=str(item.get("id", name)),
                sourceId=source.source_id,
                sourceType=source.source_type,
                name=name,
                target=_target_from_name(name),
                headSha=head_sha,
                sizeInBytes=item.get("size_in_bytes"),
                expired=bool(item.get("expired", False)),
                archiveDownloadUrlRedacted=_redact_url(item.get("archive_download_url")),
                metadataRedacted={
                    "name": name,
                    "expired": bool(item.get("expired", False)),
                    "archive_download_url": _redact_url(item.get("archive_download_url")),
                    "api_path": item.get("url"),
                },
            )
        )
    return artifacts
