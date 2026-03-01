from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass
from typing import Any

from binliquid.core.llm_ollama import LLMClient
from binliquid.schemas.models import ExpertName, PlannerOutput, ResponseMode, TaskType
from binliquid.schemas.reason_codes import ReasonCode

PLANNER_SYSTEM_PROMPT = """
You are a strict planner. Return only valid JSON that exactly matches the required fields.
Required fields: task_type, intent, needs_expert, expert_candidates, confidence,
latency_budget_ms, can_fallback, response_mode.
No markdown, no extra keys.
""".strip()


@dataclass(slots=True)
class PlannerRun:
    output: PlannerOutput
    raw_output: str
    parse_failed: bool
    error: str | None
    elapsed_ms: int
    reason_code: ReasonCode


class Planner:
    def __init__(
        self,
        llm: LLMClient,
        default_latency_budget_ms: int = 3500,
        llm_timeout_ms: int = 60_000,
    ):
        self._llm = llm
        self._default_latency_budget_ms = default_latency_budget_ms
        self._llm_timeout_ms = llm_timeout_ms

    def plan(self, user_input: str) -> PlannerRun:
        prompt = (
            "Analyze user request and return strict JSON only.\n"
            f"User input: {user_input}\n"
            "Task types: chat, code, research, plan, mixed.\n"
            "Response modes: direct, tool-first, ask-clarify.\n"
            "Expert candidates: code_expert, research_expert, plan_expert.\n"
            "Return exactly this structure with valid values:\n"
            "{"
            '"task_type":"chat|code|research|plan|mixed",'
            '"intent":"...",'
            '"needs_expert":true,'
            '"expert_candidates":["research_expert","plan_expert","code_expert"],'
            '"confidence":0.0,'
            '"latency_budget_ms":3000,'
            '"can_fallback":true,'
            '"response_mode":"direct|tool-first|ask-clarify"'
            "}"
        )

        started = time.perf_counter()
        raw_output = ""
        try:
            raw_output = self._generate_with_timeout(
                prompt=prompt,
                system=PLANNER_SYSTEM_PROMPT,
                json_mode=True,
            )
        except Exception as exc:  # noqa: BLE001
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            fallback = self._heuristic_plan(user_input=user_input, intent="planner_llm_failure")
            return PlannerRun(
                output=fallback,
                raw_output=raw_output,
                parse_failed=True,
                error=str(exc),
                elapsed_ms=elapsed_ms,
                reason_code=ReasonCode.PLANNER_LLM_FAILURE,
            )

        try:
            payload, repaired = self._parse_json_payload(raw_output)
        except Exception as exc:  # noqa: BLE001
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            fallback = self._heuristic_plan(user_input=user_input, intent="planner_parse_fallback")
            return PlannerRun(
                output=fallback,
                raw_output=raw_output,
                parse_failed=True,
                error=str(exc),
                elapsed_ms=elapsed_ms,
                reason_code=ReasonCode.PLANNER_PARSE_FALLBACK,
            )

        try:
            payload = self._normalize_payload(payload)
            output = PlannerOutput.model_validate(payload)
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return PlannerRun(
                output=output,
                raw_output=raw_output,
                parse_failed=False,
                error=None,
                elapsed_ms=elapsed_ms,
                reason_code=(
                    ReasonCode.PLANNER_REPAIR_APPLIED if repaired else ReasonCode.PLANNER_OK
                ),
            )
        except Exception as exc:  # noqa: BLE001
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            fallback = self._heuristic_plan(user_input=user_input, intent="planner_parse_fallback")
            return PlannerRun(
                output=fallback,
                raw_output=raw_output,
                parse_failed=True,
                error=str(exc),
                elapsed_ms=elapsed_ms,
                reason_code=ReasonCode.PLANNER_SCHEMA_INVALID,
            )

    @staticmethod
    def _parse_json_payload(raw_output: str) -> tuple[dict[str, object], bool]:
        text = raw_output.strip()
        if not text:
            raise ValueError("empty planner output")

        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed, False
        except json.JSONDecodeError:
            pass

        candidate = Planner._extract_json_object(text)
        try:
            parsed = json.loads(candidate)
            repaired = candidate.strip() != text.strip()
        except json.JSONDecodeError:
            repaired_candidate = Planner._repair_json_object(candidate)
            parsed = json.loads(repaired_candidate)
            repaired = True
        if not isinstance(parsed, dict):
            raise ValueError("planner output JSON is not an object")
        return parsed, repaired

    @staticmethod
    def _extract_json_object(text: str) -> str:
        cleaned = text.replace("```json", "```").replace("```JSON", "```")
        if "```" in cleaned:
            parts = cleaned.split("```")
            for part in parts:
                part = part.strip()
                if part.startswith("{") and part.endswith("}"):
                    return part

        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise ValueError("no JSON object found in planner output")
        return cleaned[start : end + 1]

    @staticmethod
    def _repair_json_object(text: str) -> str:
        repaired = text.strip()
        repaired = re.sub(r",(\s*[}\]])", r"\1", repaired)
        repaired = repaired.replace("“", '"').replace("”", '"').replace("’", "'")
        if "'" in repaired and '"' not in repaired:
            repaired = repaired.replace("'", '"')
        return repaired

    @staticmethod
    def _normalize_payload(payload: dict[str, object]) -> dict[str, object]:
        allowed = {
            "task_type",
            "intent",
            "needs_expert",
            "expert_candidates",
            "confidence",
            "latency_budget_ms",
            "can_fallback",
            "response_mode",
        }
        extra = sorted(set(payload.keys()) - allowed)
        if extra:
            raise ValueError(f"unknown planner fields: {', '.join(extra)}")

        normalized = dict(payload)
        normalized["task_type"] = Planner._coerce_task_type(normalized.get("task_type", "chat"))
        normalized["response_mode"] = Planner._coerce_response_mode(
            normalized.get("response_mode", "direct")
        )
        normalized["intent"] = str(normalized.get("intent", "unknown_intent"))
        normalized["needs_expert"] = Planner._coerce_bool(normalized.get("needs_expert", False))
        normalized["can_fallback"] = Planner._coerce_bool(normalized.get("can_fallback", True))
        normalized["confidence"] = Planner._coerce_float(normalized.get("confidence", 0.0))
        normalized["latency_budget_ms"] = Planner._coerce_int(
            normalized.get("latency_budget_ms", 3000)
        )

        candidates = normalized.get("expert_candidates", [])
        if isinstance(candidates, list):
            normalized["expert_candidates"] = [
                Planner._coerce_expert_name(item) for item in candidates
            ]
        else:
            raise ValueError("expert_candidates must be a list")

        return normalized

    @staticmethod
    def _coerce_bool(value: object) -> bool:
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            lowered = value.strip().lower()
            if lowered in {"true", "1", "yes", "y", "on"}:
                return True
            if lowered in {"false", "0", "no", "n", "off"}:
                return False
        raise ValueError(f"invalid bool: {value!r}")

    @staticmethod
    def _coerce_float(value: object) -> float:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            return float(value.strip())
        raise ValueError(f"invalid float: {value!r}")

    @staticmethod
    def _coerce_int(value: object) -> int:
        if isinstance(value, bool):
            raise ValueError(f"invalid int: {value!r}")
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            return int(value.strip())
        raise ValueError(f"invalid int: {value!r}")

    @staticmethod
    def _coerce_task_type(value: object) -> TaskType:
        text = str(value)
        if text not in TaskType._value2member_map_:
            raise ValueError(f"invalid task_type: {value!r}")
        return TaskType(text)

    @staticmethod
    def _coerce_response_mode(value: object) -> ResponseMode:
        text = str(value)
        if text not in ResponseMode._value2member_map_:
            raise ValueError(f"invalid response_mode: {value!r}")
        return ResponseMode(text)

    @staticmethod
    def _coerce_expert_name(value: Any) -> ExpertName:
        text = str(value)
        if text not in ExpertName._value2member_map_:
            raise ValueError(f"invalid expert candidate: {value!r}")
        return ExpertName(text)

    def _heuristic_plan(self, user_input: str, intent: str) -> PlannerOutput:
        text = user_input.lower()
        code_tokens = ("python", "bug", "hata", "test", "refactor", "kod")
        research_tokens = (
            "özet",
            "summary",
            "araştır",
            "doküman",
            "document",
            "compare",
            "karşılaştır",
        )
        plan_tokens = ("plan", "adım", "takvim", "roadmap", "schedule", "hafta", "faz")

        is_code = any(token in text for token in code_tokens)
        is_research = any(token in text for token in research_tokens)
        is_plan = any(token in text for token in plan_tokens)

        if sum((is_code, is_research, is_plan)) >= 2:
            task_type = TaskType.MIXED
            candidates = [ExpertName.RESEARCH, ExpertName.PLAN, ExpertName.CODE]
            needs_expert = True
            response_mode = ResponseMode.TOOL_FIRST
            confidence = 0.62
        elif is_code:
            task_type = TaskType.CODE
            candidates = [ExpertName.CODE, ExpertName.PLAN]
            needs_expert = True
            response_mode = ResponseMode.TOOL_FIRST
            confidence = 0.62
        elif is_research:
            task_type = TaskType.RESEARCH
            candidates = [ExpertName.RESEARCH, ExpertName.PLAN]
            needs_expert = True
            response_mode = ResponseMode.TOOL_FIRST
            confidence = 0.62
        elif is_plan:
            task_type = TaskType.PLAN
            candidates = [ExpertName.PLAN, ExpertName.RESEARCH]
            needs_expert = True
            response_mode = ResponseMode.TOOL_FIRST
            confidence = 0.60
        else:
            task_type = TaskType.CHAT
            candidates = []
            needs_expert = False
            response_mode = ResponseMode.DIRECT
            confidence = 0.50

        return PlannerOutput(
            task_type=task_type,
            intent=intent,
            needs_expert=needs_expert,
            expert_candidates=candidates,
            confidence=confidence,
            latency_budget_ms=self._default_latency_budget_ms,
            can_fallback=True,
            response_mode=response_mode,
        )

    def _generate_with_timeout(self, prompt: str, system: str, json_mode: bool) -> str:
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(
            self._llm.generate,
            prompt,
            system,
            json_mode,
        )
        try:
            return future.result(timeout=self._llm_timeout_ms / 1000)
        except TimeoutError as exc:
            future.cancel()
            raise TimeoutError("planner llm timeout") from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
