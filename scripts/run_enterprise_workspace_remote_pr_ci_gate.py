from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BRANCH = "codex/enterprise-workspace-onboarding-agent-enrollment-v1"
DEFAULT_BASE_BRANCH = "main"
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "artifacts" / "enterprise-workspace-remote-pr-ci"
DEFAULT_RELEASE_CLOSURE_REPORT = (
    REPO_ROOT / "artifacts" / "enterprise-workspace-release-closure" / "closure_report.json"
)
DEFAULT_PR_READINESS_REPORT = (
    REPO_ROOT / "artifacts" / "enterprise-workspace-pr-readiness" / "pr_readiness_report.json"
)
DEFAULT_PR_BODY = REPO_ROOT / "artifacts" / "enterprise-workspace-pr-readiness" / "pr_body_final.md"
EXACT_REMOTE_APPROVAL = "ONAY: Branch'i remote'a push et ve draft PR aç."

RAW_MARKERS = (
    "rawToken",
    "shown-once-token-test-value",
    "BEGIN PRIVATE KEY",
    "Authorization: Bearer",
    "password=",
    "secret=",
    "api_key",
    "private_key",
)

CLAIM_OVERREACH_MARKERS = (
    "public GA",
    "unrestricted production",
    "fully qualified for production",
)

FORBIDDEN_COMMAND_MARKERS = (
    "--force",
    "push -f",
    "reset --hard",
    "branch -D",
    "gh pr merge",
)


class ApprovalDecision(BaseModel):
    allowed: bool
    reason_code: str = Field(alias="reasonCode")


class GitState(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    branch: str
    expected_branch: str = Field(alias="expectedBranch")
    base_branch: str = Field(alias="baseBranch")
    head_sha: str = Field(alias="headSha")
    base_sha: str = Field(alias="baseSha")
    git_status_short: str = Field(alias="gitStatusShort")
    remote_url: str = Field(alias="remoteUrl")
    ahead_behind: str = Field(alias="aheadBehind")
    remote_head_sha: str | None = Field(default=None, alias="remoteHeadSha")
    error: str | None = None


class LocalEvidenceRef(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    release_closure_report: str = Field(alias="releaseClosureReport")
    pr_readiness_report: str = Field(alias="prReadinessReport")
    release_closure_status: Literal["pass", "fail", "missing"] = Field(
        alias="releaseClosureStatus"
    )
    pr_readiness_status: Literal["pass", "fail", "missing"] = Field(alias="prReadinessStatus")
    release_closure_head_sha: str | None = Field(default=None, alias="releaseClosureHeadSha")
    pr_readiness_head_sha: str | None = Field(default=None, alias="prReadinessHeadSha")
    raw_leak_scan_status: str | None = Field(default=None, alias="rawLeakScanStatus")


class PullRequestMetadata(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    number: int
    url: str
    title: str
    draft: bool
    base_ref_name: str = Field(alias="baseRefName")
    head_ref_name: str = Field(alias="headRefName")
    head_sha: str = Field(alias="headSha")
    base_sha: str = Field(alias="baseSha")
    changed_files: int | None = Field(default=None, alias="changedFiles")
    additions: int | None = None
    deletions: int | None = None


class CiCheckSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    workflow_name: str | None = Field(default=None, alias="workflowName")
    status: Literal["queued", "in_progress", "completed", "pending", "unknown"]
    conclusion: str | None = None
    required: bool
    url: str | None = None
    started_at_utc: str | None = Field(default=None, alias="startedAtUtc")
    completed_at_utc: str | None = Field(default=None, alias="completedAtUtc")
    duration_ms: int | None = Field(default=None, alias="durationMs")
    reason_code: str = Field(alias="reasonCode")
    tail: list[str] = Field(default_factory=list)


class CiSummary(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: Literal["pass", "fail", "pending", "missing"]
    checks: list[CiCheckSummary]
    required_total: int = Field(alias="requiredTotal")
    required_passed: int = Field(alias="requiredPassed")
    required_failed: int = Field(alias="requiredFailed")
    required_pending: int = Field(alias="requiredPending")


class ReconciliationResult(BaseModel):
    ready: bool
    reasons: list[str]
    head_sha_matches_pr: bool = Field(alias="headShaMatchesPr")
    head_sha_matches_local_evidence: bool = Field(alias="headShaMatchesLocalEvidence")
    required_ci_passed: bool = Field(alias="requiredCiPassed")
    branch_clean: bool = Field(alias="branchClean")


class RemotePrCiReport(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    schema_version: Literal["enterprise-workspace.remote-pr-ci/v1"] = Field(
        alias="schemaVersion"
    )
    status: Literal["pass", "fail", "blocked", "conditional"]
    profile: str
    branch: str
    base_branch: str = Field(alias="baseBranch")
    head_sha: str = Field(alias="headSha")
    git: GitState
    pr: PullRequestMetadata | None
    local_evidence: LocalEvidenceRef = Field(alias="localEvidence")
    ci: CiSummary
    reconciliation: ReconciliationResult
    no_ship_blockers: list[str] = Field(alias="noShipBlockers")
    warnings: list[str]
    remote_push_performed: bool = Field(alias="remotePushPerformed")
    pr_created: bool = Field(alias="prCreated")
    merge_performed: Literal[False] = Field(alias="mergePerformed")
    generated_at_utc: str = Field(alias="generatedAtUtc")


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _relative(path: Path, repo_root: Path = REPO_ROOT) -> str:
    try:
        return path.relative_to(repo_root).as_posix()
    except ValueError:
        return str(path)


def _redact(value: str, repo_root: Path = REPO_ROOT) -> str:
    redacted = value.replace(str(repo_root), "<repo>").replace(str(Path.home()), "<home>")
    redacted = re.sub(
        r"(?i)(api[_-]?key|private[_-]?key|password|secret|token)\s*[:=]\s*\S+",
        r"\1=<redacted>",
        redacted,
    )
    redacted = re.sub(r"gho_[A-Za-z0-9_]+", "gho_<redacted>", redacted)
    redacted = re.sub(r"sk-[A-Za-z0-9_-]+", "sk-<redacted>", redacted)
    return redacted


def _resolve(command: list[str]) -> list[str]:
    executable = command[0]
    candidates = [executable]
    if os.name == "nt" and Path(executable).suffix == "":
        candidates = [f"{executable}.cmd", f"{executable}.exe", executable]
    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return [resolved, *command[1:]]
    return command


def _run(
    command: list[str],
    *,
    repo_root: Path = REPO_ROOT,
    timeout: int = 120,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            _resolve(command),
            cwd=repo_root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as exc:
        return subprocess.CompletedProcess(command, 127, "", str(exc))


def _git_text(args: list[str], *, repo_root: Path = REPO_ROOT) -> str:
    result = _run(["git", *args], repo_root=repo_root)
    return result.stdout.strip() if result.returncode == 0 else ""


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def remote_operation_allowed(*, allow_remote: bool, approval_text: str | None) -> ApprovalDecision:
    if not allow_remote:
        return ApprovalDecision(allowed=False, reasonCode="REMOTE_OPERATION_DISABLED")
    if approval_text != EXACT_REMOTE_APPROVAL:
        return ApprovalDecision(allowed=False, reasonCode="REMOTE_APPROVAL_MISSING")
    return ApprovalDecision(allowed=True, reasonCode="OK")


def collect_git_state(
    *,
    expected_branch: str,
    base_branch: str = DEFAULT_BASE_BRANCH,
    repo_root: Path = REPO_ROOT,
) -> GitState:
    branch = _git_text(["branch", "--show-current"], repo_root=repo_root)
    head = _git_text(["rev-parse", "HEAD"], repo_root=repo_root)
    base_ref = f"origin/{base_branch}"
    base = _git_text(["rev-parse", base_ref], repo_root=repo_root)
    status = _git_text(["status", "--short", "--untracked-files=no"], repo_root=repo_root)
    remote = _git_text(["remote", "get-url", "origin"], repo_root=repo_root)
    ahead_behind = _git_text(
        ["rev-list", "--left-right", "--count", f"{base_ref}...HEAD"],
        repo_root=repo_root,
    )
    remote_head_text = _git_text(
        ["ls-remote", "--heads", "origin", expected_branch],
        repo_root=repo_root,
    )
    remote_head = remote_head_text.split()[0] if remote_head_text else None
    return GitState(
        branch=branch,
        expectedBranch=expected_branch,
        baseBranch=base_branch,
        headSha=head,
        baseSha=base,
        gitStatusShort=status,
        remoteUrl=remote,
        aheadBehind=ahead_behind,
        remoteHeadSha=remote_head,
    )


def load_local_evidence(
    *,
    release_closure_path: Path,
    pr_readiness_path: Path,
    repo_root: Path = REPO_ROOT,
) -> LocalEvidenceRef:
    def read_status(
        path: Path,
    ) -> tuple[Literal["pass", "fail", "missing"], str | None, dict[str, Any]]:
        if not path.exists():
            return "missing", None, {}
        try:
            payload = _load_json(path)
        except (OSError, json.JSONDecodeError):
            return "fail", None, {}
        status = "pass" if payload.get("status") == "pass" else "fail"
        head = payload.get("headSha")
        return status, str(head) if head else None, payload

    closure_status, closure_head, closure_payload = read_status(release_closure_path)
    readiness_status, readiness_head, readiness_payload = read_status(pr_readiness_path)
    raw_status = readiness_payload.get("rawLeakScan", {}).get("status") or closure_payload.get(
        "rawLeakScan", {}
    ).get("status")
    return LocalEvidenceRef(
        releaseClosureReport=_relative(release_closure_path, repo_root),
        prReadinessReport=_relative(pr_readiness_path, repo_root),
        releaseClosureStatus=closure_status,
        prReadinessStatus=readiness_status,
        releaseClosureHeadSha=closure_head,
        prReadinessHeadSha=readiness_head,
        rawLeakScanStatus=raw_status,
    )


def _normalize_pr_payload(payload: dict[str, Any]) -> PullRequestMetadata:
    return PullRequestMetadata(
        number=int(payload["number"]),
        url=str(payload["url"]),
        title=str(payload.get("title") or ""),
        draft=bool(payload.get("draft", payload.get("isDraft", False))),
        baseRefName=str(payload.get("baseRefName") or ""),
        headRefName=str(payload.get("headRefName") or ""),
        headSha=str(payload.get("headSha") or payload.get("headRefOid") or ""),
        baseSha=str(payload.get("baseSha") or payload.get("baseRefOid") or ""),
        changedFiles=payload.get("changedFiles"),
        additions=payload.get("additions"),
        deletions=payload.get("deletions"),
    )


def collect_pr_metadata(
    *,
    branch: str,
    pr_number: int | None = None,
    pr_fixture: Path | None = None,
    skip_gh: bool = False,
    repo_root: Path = REPO_ROOT,
) -> PullRequestMetadata | None:
    if pr_fixture:
        payload = _load_json(pr_fixture)
        if isinstance(payload, list):
            payload = payload[0] if payload else {}
        return _normalize_pr_payload(payload)
    if skip_gh:
        return None
    fields = (
        "number,url,title,isDraft,baseRefName,headRefName,headRefOid,baseRefOid,"
        "changedFiles,additions,deletions"
    )
    command = ["gh", "pr", "view", "--json", fields]
    if pr_number is not None:
        command.insert(3, str(pr_number))
    else:
        command.insert(3, branch)
    result = _run(command, repo_root=repo_root, timeout=120)
    if result.returncode != 0 or not result.stdout.strip():
        return None
    return _normalize_pr_payload(json.loads(result.stdout))


def _normalize_check_payload(payload: dict[str, Any]) -> CiCheckSummary:
    status = str(payload.get("status") or payload.get("state") or "unknown").lower()
    conclusion = payload.get("conclusion")
    conclusion = str(conclusion).lower() if conclusion is not None else None
    if status in {"success", "failure", "cancelled", "skipped"}:
        status = "completed"
    if status not in {"queued", "in_progress", "completed", "pending"}:
        status = "unknown"
    required = bool(payload.get("required", True))
    if status in {"queued", "in_progress", "pending"}:
        reason = "CI_PENDING" if required else "OPTIONAL_CI_PENDING"
    elif conclusion in {"success", "neutral"}:
        reason = "OK"
    elif conclusion == "skipped" and required:
        reason = "CI_SKIPPED_REQUIRED"
    elif required:
        reason = "CI_FAILED"
    else:
        reason = "OPTIONAL_CI_FAILED"
    return CiCheckSummary(
        name=str(payload.get("name") or payload.get("workflowName") or "unknown"),
        workflowName=payload.get("workflowName"),
        status=status,  # type: ignore[arg-type]
        conclusion=conclusion,
        required=required,
        url=payload.get("url") or payload.get("link"),
        startedAtUtc=payload.get("startedAt") or payload.get("startedAtUtc"),
        completedAtUtc=payload.get("completedAt") or payload.get("completedAtUtc"),
        durationMs=payload.get("durationMs"),
        reasonCode=reason,
        tail=[_redact(str(line)) for line in payload.get("tail", [])[:50]],
    )


def _summarize_ci(checks: list[CiCheckSummary]) -> CiSummary:
    required = [check for check in checks if check.required]
    passed = [
        check
        for check in required
        if check.status == "completed" and check.conclusion in {"success", "neutral"}
    ]
    failed = [
        check
        for check in required
        if check.status == "completed" and check.conclusion not in {"success", "neutral"}
    ]
    pending = [check for check in required if check.status in {"queued", "in_progress", "pending"}]
    if not checks:
        status: Literal["pass", "fail", "pending", "missing"] = "missing"
    elif failed:
        status = "fail"
    elif pending:
        status = "pending"
    elif len(passed) == len(required):
        status = "pass"
    else:
        status = "missing"
    return CiSummary(
        status=status,
        checks=checks,
        requiredTotal=len(required),
        requiredPassed=len(passed),
        requiredFailed=len(failed),
        requiredPending=len(pending),
    )


def collect_ci_checks(
    *,
    branch: str,
    pr_number: int | None = None,
    ci_fixture: Path | None = None,
    head_sha: str | None = None,
    wait_ci: bool = False,
    timeout_seconds: int = 1800,
    skip_gh: bool = False,
    repo_root: Path = REPO_ROOT,
) -> CiSummary:
    if ci_fixture:
        payload = _load_json(ci_fixture)
        if isinstance(payload, dict):
            payload = payload.get("checks", [])
        if head_sha:
            payload = [
                item
                for item in payload
                if not item.get("headSha") or item.get("headSha") == head_sha
            ]
        return _summarize_ci([_normalize_check_payload(item) for item in payload])
    if skip_gh:
        return _summarize_ci([])
    if wait_ci:
        _run(["gh", "pr", "checks", "--watch"], repo_root=repo_root, timeout=timeout_seconds)
    fields = "name,bucket,state,conclusion,link,startedAt,completedAt"
    command = ["gh", "pr", "checks", "--json", fields]
    if pr_number is not None:
        command.insert(3, str(pr_number))
    result = _run(command, repo_root=repo_root, timeout=120)
    if result.returncode != 0 or not result.stdout.strip():
        runs = _run(
            [
                "gh",
                "run",
                "list",
                "--branch",
                branch,
                "--limit",
                "20",
                "--json",
                "displayTitle,headSha,status,conclusion,workflowName,url,createdAt,updatedAt",
            ],
            repo_root=repo_root,
            timeout=120,
        )
        if runs.returncode != 0 or not runs.stdout.strip():
            return _summarize_ci([])
        payload = json.loads(runs.stdout)
        if head_sha:
            payload = [item for item in payload if item.get("headSha") == head_sha]
        return _summarize_ci(
            [
                _normalize_check_payload(
                    {
                        "name": item.get("displayTitle") or item.get("workflowName"),
                        "workflowName": item.get("workflowName"),
                        "status": item.get("status"),
                        "conclusion": item.get("conclusion"),
                        "url": item.get("url"),
                        "startedAt": item.get("createdAt"),
                        "completedAt": item.get("updatedAt"),
                        "required": True,
                    }
                )
                for item in payload
            ]
        )
    return _summarize_ci([_normalize_check_payload(item) for item in json.loads(result.stdout)])


def _scan_text(path: Path) -> list[str]:
    if not path.exists() or not path.is_file():
        return []
    text = path.read_text(encoding="utf-8", errors="ignore")
    findings = [f"RAW_LEAK_DETECTED:{marker}" for marker in RAW_MARKERS if marker in text]
    findings.extend(
        f"CLAIM_OVERREACH:{marker}" for marker in CLAIM_OVERREACH_MARKERS if marker in text
    )
    return findings


def reconcile_remote_pr_ci(
    *,
    git_state: GitState,
    local_evidence: LocalEvidenceRef,
    pr: PullRequestMetadata | None,
    ci: CiSummary,
    expected_branch: str,
    base_branch: str,
    pr_body_path: Path = DEFAULT_PR_BODY,
) -> tuple[ReconciliationResult, list[str], list[str]]:
    blockers: list[str] = []
    warnings: list[str] = []
    if git_state.branch != expected_branch:
        blockers.append("WRONG_BRANCH")
    if git_state.git_status_short:
        blockers.append("DIRTY_WORKTREE")
    if local_evidence.release_closure_status != "pass":
        blockers.append("LOCAL_RELEASE_CLOSURE_FAILED")
    if local_evidence.pr_readiness_status != "pass":
        blockers.append("LOCAL_PR_READINESS_FAILED")
    if local_evidence.raw_leak_scan_status not in {None, "pass"}:
        blockers.append("RAW_LEAK_DETECTED")
    local_heads = [
        local_evidence.release_closure_head_sha,
        local_evidence.pr_readiness_head_sha,
    ]
    local_match = all(head in {None, git_state.head_sha} for head in local_heads)
    if not local_match:
        blockers.append("LOCAL_EVIDENCE_HEAD_SHA_MISMATCH")
    pr_match = True
    if pr is None:
        warnings.append("PR metadata is missing; remote PR closure cannot be final.")
    else:
        if pr.base_ref_name != base_branch:
            blockers.append("PR_BASE_MISMATCH")
        if pr.head_ref_name != expected_branch:
            blockers.append("PR_HEAD_BRANCH_MISMATCH")
        if pr.head_sha != git_state.head_sha:
            pr_match = False
            blockers.append("PR_HEAD_SHA_MISMATCH")
        if not pr.draft:
            warnings.append("PR is not draft; verify review boundary before merge readiness.")
    if ci.status == "missing":
        warnings.append("CI checks are missing; run after PR/checks are available.")
    if ci.required_failed:
        blockers.append("CI_REQUIRED_CHECK_FAILED")
    if any(check.reason_code == "CI_SKIPPED_REQUIRED" for check in ci.checks):
        blockers.append("CI_SKIPPED_REQUIRED")
    if ci.required_pending:
        blockers.append("CI_REQUIRED_CHECK_PENDING")
    for check in ci.checks:
        if not check.required and check.reason_code in {
            "OPTIONAL_CI_FAILED",
            "OPTIONAL_CI_PENDING",
        }:
            warnings.append(f"Optional check not green: {check.name}")
    blockers.extend(_scan_text(pr_body_path))
    ready = not blockers and pr is not None and ci.status == "pass"
    reconciliation = ReconciliationResult(
        ready=ready,
        reasons=sorted(set(blockers + ([] if ready else warnings))),
        headShaMatchesPr=pr_match,
        headShaMatchesLocalEvidence=local_match,
        requiredCiPassed=ci.status == "pass",
        branchClean=not bool(git_state.git_status_short),
    )
    return reconciliation, sorted(set(blockers)), warnings


def write_post_pr_commands(
    *,
    branch: str,
    base_branch: str,
    pr_body_path: Path,
    output_path: Path,
) -> None:
    text = (
        "# Enterprise Workspace Remote PR CI Commands\n\n"
        "Remote operations require an explicit approval boundary. No merge command is included.\n\n"
        "## Required approval\n\n"
        f"`{EXACT_REMOTE_APPROVAL}`\n\n"
        "## Push and draft PR\n\n"
        "```bash\n"
        f"git push -u origin {branch}\n"
        "gh pr create \\\n"
        "  --draft \\\n"
        f"  --base {base_branch} \\\n"
        f"  --head {branch} \\\n"
        "  --title \"Enterprise Workspace Onboarding & Agent Enrollment v1\" \\\n"
        f"  --body-file {_relative(pr_body_path)}\n"
        "```\n\n"
        "## CI evidence collection\n\n"
        "```bash\n"
        "gh pr checks --watch\n"
        "gh pr checks --json name,bucket,state,conclusion,link,startedAt,completedAt\n"
        f"gh run list --branch {branch} --limit 20\n"
        "```\n"
    )
    forbidden = [marker for marker in FORBIDDEN_COMMAND_MARKERS if marker in text]
    if forbidden:
        raise ValueError(f"forbidden command marker in generated commands: {forbidden}")
    output_path.write_text(text, encoding="utf-8")


def write_remote_pr_ci_markdown(*, report: RemotePrCiReport, output_path: Path) -> None:
    lines = [
        "# Enterprise Workspace Remote PR CI Closure",
        "",
        f"- Status: `{report.status}`",
        f"- Branch: `{report.branch}`",
        f"- Base: `{report.base_branch}`",
        f"- Head SHA: `{report.head_sha}`",
        f"- PR: `{report.pr.url if report.pr else 'missing'}`",
        f"- CI: `{report.ci.status}`",
        f"- Merge readiness: `{report.reconciliation.ready}`",
        f"- Remote push performed: `{report.remote_push_performed}`",
        f"- PR created: `{report.pr_created}`",
        f"- Merge performed: `{report.merge_performed}`",
        "",
        "## Required Checks",
    ]
    for check in report.ci.checks:
        if check.required:
            lines.append(f"- `{check.reason_code}` `{check.name}` `{check.conclusion}`")
    if report.no_ship_blockers:
        lines.extend(["", "## No-Ship Blockers"])
        lines.extend(f"- `{blocker}`" for blocker in report.no_ship_blockers)
    if report.warnings:
        lines.extend(["", "## Warnings"])
        lines.extend(f"- {warning}" for warning in report.warnings)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_merge_readiness(*, report: RemotePrCiReport, output_path: Path) -> None:
    lines = [
        "# Enterprise Workspace Merge Readiness",
        "",
        f"- Ready: `{report.reconciliation.ready}`",
        f"- Head SHA matches PR: `{report.reconciliation.head_sha_matches_pr}`",
        "- Head SHA matches local evidence: "
        f"`{report.reconciliation.head_sha_matches_local_evidence}`",
        f"- Required CI passed: `{report.reconciliation.required_ci_passed}`",
        f"- Branch clean: `{report.reconciliation.branch_clean}`",
        f"- Merge performed: `{report.merge_performed}`",
    ]
    if report.reconciliation.reasons:
        lines.extend(["", "## Reasons"])
        lines.extend(f"- `{reason}`" for reason in report.reconciliation.reasons)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_remote_pr_ci_gate(
    *,
    profile: str,
    branch: str = DEFAULT_BRANCH,
    base_branch: str = DEFAULT_BASE_BRANCH,
    output_root: Path = DEFAULT_OUTPUT_ROOT,
    allow_remote: bool = False,
    approval_text: str | None = None,
    pr_number: int | None = None,
    pr_url: str | None = None,
    ci_fixture: Path | None = None,
    pr_fixture: Path | None = None,
    wait_ci: bool = False,
    ci_timeout_seconds: int = 1800,
    skip_gh: bool = False,
    release_closure_path: Path = DEFAULT_RELEASE_CLOSURE_REPORT,
    pr_readiness_path: Path = DEFAULT_PR_READINESS_REPORT,
    repo_root: Path = REPO_ROOT,
) -> RemotePrCiReport:
    output_root.mkdir(parents=True, exist_ok=True)
    approval = remote_operation_allowed(allow_remote=allow_remote, approval_text=approval_text)
    git_state = collect_git_state(
        expected_branch=branch,
        base_branch=base_branch,
        repo_root=repo_root,
    )
    local_evidence = load_local_evidence(
        release_closure_path=release_closure_path,
        pr_readiness_path=pr_readiness_path,
        repo_root=repo_root,
    )
    warnings: list[str] = []
    blockers: list[str] = []
    remote_push_performed = False
    pr_created = False
    if allow_remote and not approval.allowed:
        blockers.append(approval.reason_code)

    pr = collect_pr_metadata(
        branch=branch,
        pr_number=pr_number,
        pr_fixture=pr_fixture,
        skip_gh=skip_gh,
        repo_root=repo_root,
    )
    if pr_url and pr is None:
        warnings.append(f"PR URL provided but metadata unavailable: {_redact(pr_url, repo_root)}")
    ci = collect_ci_checks(
        branch=branch,
        pr_number=pr_number,
        ci_fixture=ci_fixture,
        head_sha=git_state.head_sha,
        wait_ci=wait_ci,
        timeout_seconds=ci_timeout_seconds,
        skip_gh=skip_gh,
        repo_root=repo_root,
    )
    reconciliation, reconciliation_blockers, reconciliation_warnings = reconcile_remote_pr_ci(
        git_state=git_state,
        local_evidence=local_evidence,
        pr=pr,
        ci=ci,
        expected_branch=branch,
        base_branch=base_branch,
    )
    blockers.extend(reconciliation_blockers)
    warnings.extend(reconciliation_warnings)
    blockers = sorted(set(blockers))
    if any(blocker == "CI_REQUIRED_CHECK_PENDING" for blocker in blockers):
        status: Literal["pass", "fail", "blocked", "conditional"] = "conditional"
    elif blockers:
        status = "blocked"
    elif reconciliation.ready:
        status = "pass"
    else:
        status = "conditional"
    report = RemotePrCiReport(
        schemaVersion="enterprise-workspace.remote-pr-ci/v1",
        status=status,
        profile=profile,
        branch=git_state.branch,
        baseBranch=base_branch,
        headSha=git_state.head_sha,
        git=git_state,
        pr=pr,
        localEvidence=local_evidence,
        ci=ci,
        reconciliation=reconciliation,
        noShipBlockers=blockers,
        warnings=warnings,
        remotePushPerformed=remote_push_performed,
        prCreated=pr_created,
        mergePerformed=False,
        generatedAtUtc=_now(),
    )

    _write_json(output_root / "remote_pr_ci_report.json", report.model_dump(by_alias=True))
    _write_json(output_root / "ci_checks.json", ci.model_dump(by_alias=True))
    if pr is not None:
        _write_json(output_root / "pr_metadata.json", pr.model_dump(by_alias=True))
    write_remote_pr_ci_markdown(report=report, output_path=output_root / "remote_pr_ci_report.md")
    write_merge_readiness(report=report, output_path=output_root / "merge_readiness.md")
    write_post_pr_commands(
        branch=branch,
        base_branch=base_branch,
        pr_body_path=DEFAULT_PR_BODY,
        output_path=output_root / "post_pr_commands.md",
    )
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run enterprise workspace remote PR CI gate.")
    parser.add_argument("--profile", default="enterprise")
    parser.add_argument("--branch", default=DEFAULT_BRANCH)
    parser.add_argument("--base", default=DEFAULT_BASE_BRANCH, dest="base_branch")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--pr-number", type=int)
    parser.add_argument("--pr-url")
    parser.add_argument("--allow-remote", action="store_true")
    parser.add_argument("--approval-text")
    parser.add_argument("--ci-fixture", type=Path)
    parser.add_argument("--pr-fixture", type=Path)
    parser.add_argument("--wait-ci", action="store_true")
    parser.add_argument("--ci-timeout-seconds", type=int, default=1800)
    parser.add_argument("--skip-gh", action="store_true")
    parser.add_argument("--release-closure-path", type=Path, default=DEFAULT_RELEASE_CLOSURE_REPORT)
    parser.add_argument("--pr-readiness-path", type=Path, default=DEFAULT_PR_READINESS_REPORT)
    parser.add_argument("--json", action="store_true", dest="json_output")
    args = parser.parse_args(argv)

    report = run_remote_pr_ci_gate(
        profile=args.profile,
        branch=args.branch,
        base_branch=args.base_branch,
        output_root=args.output_root,
        allow_remote=args.allow_remote,
        approval_text=args.approval_text,
        pr_number=args.pr_number,
        pr_url=args.pr_url,
        ci_fixture=args.ci_fixture,
        pr_fixture=args.pr_fixture,
        wait_ci=args.wait_ci,
        ci_timeout_seconds=args.ci_timeout_seconds,
        skip_gh=args.skip_gh,
        release_closure_path=args.release_closure_path,
        pr_readiness_path=args.pr_readiness_path,
    )
    payload = report.model_dump(by_alias=True)
    if args.json_output:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(f"status={report.status} output={args.output_root}")
    return 0 if report.status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
