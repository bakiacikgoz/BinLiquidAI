from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass

from binliquid.core.llm_ollama import LLMClient
from binliquid.schemas.models import PlannerOutput, ResponseMode, TaskType

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
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            fallback = self._heuristic_plan(user_input=user_input, intent="planner_llm_failure")
            return PlannerRun(
                output=fallback,
                raw_output=raw_output,
                parse_failed=True,
                error=str(exc),
                elapsed_ms=elapsed_ms,
            )

        try:
            payload = self._parse_json_payload(raw_output)
            payload = self._normalize_payload(payload)
            output = PlannerOutput.model_validate(payload)
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return PlannerRun(
                output=output,
                raw_output=raw_output,
                parse_failed=False,
                error=None,
                elapsed_ms=elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            fallback = self._heuristic_plan(user_input=user_input, intent="planner_parse_fallback")
            return PlannerRun(
                output=fallback,
                raw_output=raw_output,
                parse_failed=True,
                error=str(exc),
                elapsed_ms=elapsed_ms,
            )

    @staticmethod
    def _parse_json_payload(raw_output: str) -> dict[str, object]:
        text = raw_output.strip()
        if not text:
            raise ValueError("empty planner output")

        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

        candidate = Planner._extract_json_object(text)
        parsed = json.loads(candidate)
        if not isinstance(parsed, dict):
            raise ValueError("planner output JSON is not an object")
        return parsed

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
    def _normalize_payload(payload: dict[str, object]) -> dict[str, object]:
        normalized = dict(payload)
        normalized["task_type"] = TaskType(str(normalized.get("task_type", "chat")))
        normalized["response_mode"] = ResponseMode(str(normalized.get("response_mode", "direct")))
        normalized["intent"] = str(normalized.get("intent", "unknown_intent"))
        normalized["needs_expert"] = bool(normalized.get("needs_expert", False))
        normalized["can_fallback"] = bool(normalized.get("can_fallback", True))
        normalized["confidence"] = float(normalized.get("confidence", 0.0))
        normalized["latency_budget_ms"] = int(normalized.get("latency_budget_ms", 3000))

        candidates = normalized.get("expert_candidates", [])
        if isinstance(candidates, list):
            normalized["expert_candidates"] = [str(item) for item in candidates]
        else:
            normalized["expert_candidates"] = []

        return normalized

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
        is_research = any(
            token in text
            for token in research_tokens
        )
        is_plan = any(token in text for token in plan_tokens)

        if sum((is_code, is_research, is_plan)) >= 2:
            task_type = TaskType.MIXED
            candidates = ["research_expert", "plan_expert", "code_expert"]
            needs_expert = True
            response_mode = ResponseMode.TOOL_FIRST
            confidence = 0.62
        elif is_code:
            task_type = TaskType.CODE
            candidates = ["code_expert", "plan_expert"]
            needs_expert = True
            response_mode = ResponseMode.TOOL_FIRST
            confidence = 0.62
        elif is_research:
            task_type = TaskType.RESEARCH
            candidates = ["research_expert", "plan_expert"]
            needs_expert = True
            response_mode = ResponseMode.TOOL_FIRST
            confidence = 0.62
        elif is_plan:
            task_type = TaskType.PLAN
            candidates = ["plan_expert", "research_expert"]
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
