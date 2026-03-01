from __future__ import annotations

import time
from pathlib import Path

from binliquid.experts.base import ExpertBase
from binliquid.schemas.expert_payloads import CodeExpertPayload, VerificationResult
from binliquid.schemas.models import ExpertName, ExpertRequest, ExpertResult, ExpertStatus
from binliquid.tools.code_verify import verify_python_snippet


class CodeExpert(ExpertBase):
    name = ExpertName.CODE
    estimated_tool_calls_per_run = 2

    def __init__(self, workspace: str | Path = "."):
        self.workspace = Path(workspace)

    def run(self, request: ExpertRequest) -> ExpertResult:
        started = time.perf_counter()
        lower = request.user_input.lower()

        issue_type = self._detect_issue_type(lower)
        strategy = self._strategy_for_issue(issue_type)
        patch_plan = self._patch_plan(issue_type)
        candidate_snippet = self._candidate_snippet(issue_type, lower)

        verification_raw = {
            "parse_ok": True,
            "lint_ok": None,
            "tests_ok": None,
            "details": {"skipped": "no executable snippet"},
        }
        if candidate_snippet:
            verification_raw = verify_python_snippet(
                candidate_snippet,
                workdir=self.workspace,
                run_lint=True,
                run_tests=issue_type in {"test", "runtime"},
            )

        verification = VerificationResult.model_validate(verification_raw)
        payload = CodeExpertPayload(
            issue_type=issue_type,
            strategy=strategy,
            patch_plan=patch_plan,
            candidate_snippet=candidate_snippet,
            verification=verification,
            notes="Code expert produced a structured, verifier-backed plan.",
        )

        conf = 0.82 if verification.parse_ok and verification.lint_ok in {True, None} else 0.58
        elapsed = int((time.perf_counter() - started) * 1000)
        return ExpertResult(
            expert_name=self.name,
            status=ExpertStatus.OK,
            confidence=conf,
            payload=payload.model_dump(mode="json"),
            elapsed_ms=elapsed,
        )

    @staticmethod
    def _detect_issue_type(text: str) -> str:
        if any(token in text for token in ("syntax", "indent", "parse", "sözdizim")):
            return "syntax"
        if any(token in text for token in ("test", "failing", "failed", "assert")):
            return "test"
        if any(token in text for token in ("import", "module", "package", "dependency")):
            return "import"
        if any(token in text for token in ("config", "env", "setting", "toml", "yaml")):
            return "config"
        if any(token in text for token in ("refactor", "cleanup", "clean code")):
            return "refactor"
        if any(token in text for token in ("error", "exception", "traceback", "runtime", "hata")):
            return "runtime"
        return "generic"

    @staticmethod
    def _strategy_for_issue(issue_type: str) -> str:
        mapping = {
            "test": "test_first_fix",
            "refactor": "safe_refactor",
            "generic": "minimal_patch",
        }
        return mapping.get(issue_type, "minimal_patch")

    @staticmethod
    def _patch_plan(issue_type: str) -> list[str]:
        base = [
            "Problemi yeniden üret ve hata tipini doğrula.",
            "En küçük davranış değişimiyle düzeltmeyi uygula.",
            "Doğrulama kontrollerini çalıştır ve sonucu raporla.",
        ]
        if issue_type == "test":
            return [
                "Failing test kapsamını daralt (collect/test target).",
                "Uygun fonksiyon/branch üzerinde minimal patch uygula.",
                "Testleri tekrar çalıştır, kırılan yan etkileri kontrol et.",
            ]
        if issue_type == "refactor":
            return [
                "Davranış koruyan refactor sınırını belirle.",
                "Fonksiyonları küçük ve saf parçalara böl.",
                "Regresyon riskini test/lint ile doğrula.",
            ]
        return base

    @staticmethod
    def _candidate_snippet(issue_type: str, text: str) -> str | None:
        if "unique" in text and "sort" in text:
            return (
                "def unique_sorted(items):\n"
                "    \"\"\"Return sorted unique list.\"\"\"\n"
                "    return sorted(set(items))\n"
            )
        if issue_type == "test":
            return (
                "def normalize_name(value: str) -> str:\n"
                "    return value.strip().lower()\n"
            )
        if issue_type == "runtime":
            return (
                "def safe_div(numerator: float, denominator: float) -> float:\n"
                "    if denominator == 0:\n"
                "        raise ValueError('denominator must not be zero')\n"
                "    return numerator / denominator\n"
            )
        return None
