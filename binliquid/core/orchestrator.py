from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError
from dataclasses import dataclass, field
from typing import Protocol
from uuid import uuid4

from binliquid.core.llm_ollama import LLMClient
from binliquid.core.planner import Planner
from binliquid.experts.base import ExpertBase
from binliquid.memory.manager import MemoryManager
from binliquid.runtime.config import RuntimeConfig
from binliquid.schemas.models import (
    ExpertRequest,
    ExpertResult,
    ExpertStatus,
    OrchestratorResult,
    PlannerOutput,
    RouterDecision,
    TaskType,
)
from binliquid.telemetry.tracer import Tracer


class RouterLike(Protocol):
    def decide(self, planner_output: PlannerOutput) -> RouterDecision:
        ...


@dataclass(slots=True)
class CircuitBreaker:
    threshold: int
    cooldown_s: int
    failures: dict[str, int] = field(default_factory=dict)
    open_until: dict[str, float] = field(default_factory=dict)

    def is_open(self, expert_name: str) -> bool:
        until = self.open_until.get(expert_name)
        return until is not None and time.monotonic() < until

    def record_failure(self, expert_name: str) -> None:
        if self.is_open(expert_name):
            return

        current = self.failures.get(expert_name, 0) + 1
        if current >= self.threshold:
            self.open_until[expert_name] = time.monotonic() + self.cooldown_s
            self.failures[expert_name] = 0
            return

        self.failures[expert_name] = current

    def record_success(self, expert_name: str) -> None:
        self.failures[expert_name] = 0


class Orchestrator:
    def __init__(
        self,
        planner: Planner,
        llm: LLMClient,
        router: RouterLike,
        experts: dict[str, ExpertBase],
        tracer: Tracer,
        config: RuntimeConfig,
        memory_manager: MemoryManager | None = None,
    ):
        self._planner = planner
        self._llm = llm
        self._router = router
        self._experts = experts
        self._tracer = tracer
        self._config = config
        self._memory_manager = memory_manager
        self._breaker = CircuitBreaker(
            threshold=config.limits.circuit_breaker_threshold,
            cooldown_s=config.limits.circuit_breaker_cooldown_s,
        )

    def process(
        self,
        user_input: str,
        session_context: dict[str, str] | None = None,
        use_router: bool = True,
    ) -> OrchestratorResult:
        started_total = time.perf_counter()
        request_id = str(uuid4())
        session_context = session_context or {}
        fallback_events: list[str] = []
        expert_latency_ms = 0

        self._tracer.emit(request_id, "request_received", {"input": user_input})

        planner_run = self._planner.plan(user_input)
        planner_output = planner_run.output
        self._tracer.emit(
            request_id,
            "planner_output",
            {
                "parse_failed": planner_run.parse_failed,
                "error": planner_run.error,
                "output": planner_output.model_dump(mode="json"),
            },
        )
        if planner_run.parse_failed:
            fallback_events.append("planner_parse_fallback")

        if use_router:
            routing_started = time.perf_counter()
            route = self._router.decide(planner_output)
            routing_elapsed = int((time.perf_counter() - routing_started) * 1000)
        else:
            route = RouterDecision(
                selected_expert="llm_only",
                selection_confidence=planner_output.confidence,
                estimated_cost=0.1,
                estimated_latency_ms=planner_output.latency_budget_ms,
                fallback_expert=None,
                reason_code="BASELINE_A",
            )
            routing_elapsed = 0
        effective_reason_code = route.reason_code
        self._tracer.emit(request_id, "router_decision", route.model_dump(mode="json"))

        selected_result: ExpertResult | None = None
        secondary_result: ExpertResult | None = None
        used_path = "llm_only"
        session_id = str(session_context.get("session_id", request_id))

        if use_router and route.selected_expert != "llm_only" and planner_output.needs_expert:
            if route.selection_confidence < self._config.router_confidence_threshold:
                fallback_events.append("router_low_confidence")
                effective_reason_code = "LOW_CONFIDENCE_GATE"
            elif self._breaker.is_open(route.selected_expert):
                fallback_events.append("CB_OPEN")
                effective_reason_code = "CB_OPEN"
                self._tracer.emit(
                    request_id,
                    "router_decision_override",
                    {"reason_code": "CB_OPEN", "expert": route.selected_expert},
                )
            else:
                selected_result = self._run_expert_with_retries(
                    request_id=request_id,
                    planner_output=planner_output,
                    expert_name=route.selected_expert,
                    user_input=user_input,
                    session_context=session_context,
                )
                expert_latency_ms += selected_result.elapsed_ms

                if selected_result.status == ExpertStatus.OK:
                    self._breaker.record_success(route.selected_expert)
                    self._update_router_feedback(
                        expert_name=route.selected_expert,
                        status=selected_result.status,
                        elapsed_ms=selected_result.elapsed_ms,
                    )
                    used_path = f"expert:{route.selected_expert}"
                else:
                    self._breaker.record_failure(route.selected_expert)
                    self._update_router_feedback(
                        expert_name=route.selected_expert,
                        status=selected_result.status,
                        elapsed_ms=selected_result.elapsed_ms,
                    )
                    fallback_events.append(f"expert_failed:{route.selected_expert}:{selected_result.status.value}")

                if selected_result.status != ExpertStatus.OK and route.fallback_expert:
                    if self._breaker.is_open(route.fallback_expert):
                        fallback_events.append("CB_OPEN_FALLBACK")
                    else:
                        fallback = self._run_expert_with_retries(
                            request_id=request_id,
                            planner_output=planner_output,
                            expert_name=route.fallback_expert,
                            user_input=user_input,
                            session_context=session_context,
                        )
                        expert_latency_ms += fallback.elapsed_ms
                        if fallback.status == ExpertStatus.OK:
                            self._breaker.record_success(route.fallback_expert)
                            self._update_router_feedback(
                                expert_name=route.fallback_expert,
                                status=fallback.status,
                                elapsed_ms=fallback.elapsed_ms,
                            )
                            selected_result = fallback
                            used_path = f"expert:{route.fallback_expert}"
                            fallback_events.append(f"fallback_expert_used:{route.fallback_expert}")
                        else:
                            self._breaker.record_failure(route.fallback_expert)
                            self._update_router_feedback(
                                expert_name=route.fallback_expert,
                                status=fallback.status,
                                elapsed_ms=fallback.elapsed_ms,
                            )
                            fallback_events.append(
                                f"fallback_expert_failed:{route.fallback_expert}:{fallback.status.value}"
                            )
                elif planner_output.task_type == TaskType.MIXED and route.fallback_expert:
                    secondary_result = self._run_expert_with_retries(
                        request_id=request_id,
                        planner_output=planner_output,
                        expert_name=route.fallback_expert,
                        user_input=user_input,
                        session_context=session_context,
                    )
                    expert_latency_ms += secondary_result.elapsed_ms
                    if secondary_result.status == ExpertStatus.OK:
                        self._breaker.record_success(route.fallback_expert)
                        self._update_router_feedback(
                            expert_name=route.fallback_expert,
                            status=secondary_result.status,
                            elapsed_ms=secondary_result.elapsed_ms,
                        )
                        fallback_events.append(f"secondary_expert_used:{route.fallback_expert}")
                    else:
                        self._breaker.record_failure(route.fallback_expert)
                        self._update_router_feedback(
                            expert_name=route.fallback_expert,
                            status=secondary_result.status,
                            elapsed_ms=secondary_result.elapsed_ms,
                        )
                        fallback_events.append(
                            f"secondary_expert_failed:{route.fallback_expert}:{secondary_result.status.value}"
                        )

        llm_started = time.perf_counter()
        llm_error: str | None = None
        if selected_result and selected_result.status == ExpertStatus.OK:
            if (
                secondary_result
                and secondary_result.status == ExpertStatus.OK
                and secondary_result.payload != selected_result.payload
            ):
                adjudication_prompt = self._build_adjudication_prompt(
                    user_input=user_input,
                    primary=selected_result,
                    secondary=secondary_result,
                )
                try:
                    final_text = self._generate_with_timeout(
                        prompt=adjudication_prompt,
                        system=None,
                    )
                except Exception as exc:
                    llm_error = str(exc)
                    final_text = self._safe_fallback_text(user_input, llm_error)
                used_path = (
                    "expert_adjudicated:"
                    f"{selected_result.expert_name}+{secondary_result.expert_name}"
                )
                fallback_events.append("expert_adjudication")
            else:
                synthesis_prompt = self._build_synthesis_prompt(user_input, selected_result)
                try:
                    final_text = self._generate_with_timeout(
                        prompt=synthesis_prompt,
                        system=None,
                    )
                except Exception as exc:
                    llm_error = str(exc)
                    final_text = self._safe_fallback_text(user_input, llm_error)
        else:
            try:
                final_text = self._generate_with_timeout(
                    prompt=f"User request: {user_input}\nRespond concisely and clearly.",
                    system="You are BinLiquid assistant in product mode.",
                )
            except Exception as exc:
                llm_error = str(exc)
                final_text = self._safe_fallback_text(user_input, llm_error)
            if use_router and route.selected_expert != "llm_only":
                fallback_events.append("llm_only_synthesis")
        llm_elapsed = int((time.perf_counter() - llm_started) * 1000)

        memory_write = {
            "written": False,
            "salience_score": 0.0,
            "reason": "memory_manager_missing",
            "record_id": None,
        }
        if self._memory_manager is not None:
            write_result = self._memory_manager.maybe_write(
                session_id=session_id,
                task_type=str(planner_output.task_type),
                user_input=user_input,
                assistant_output=final_text,
                expert_payload=selected_result.payload if selected_result else None,
            )
            memory_write = {
                "written": write_result.written,
                "salience_score": write_result.salience_score,
                "reason": write_result.reason,
                "record_id": write_result.record_id,
            }
            self._tracer.emit(request_id, "memory_write_decision", memory_write)

        total_elapsed = int((time.perf_counter() - started_total) * 1000)
        metrics = {
            "planner_latency_ms": planner_run.elapsed_ms,
            "routing_latency_ms": routing_elapsed,
            "expert_latency_ms": expert_latency_ms,
            "llm_latency_ms": llm_elapsed,
            "total_latency_ms": total_elapsed,
            "planner_parse_failed": planner_run.parse_failed,
            "router_reason_code": effective_reason_code,
            "route_selected_expert": route.selected_expert,
            "memory_written": memory_write["written"],
            "memory_salience_score": memory_write["salience_score"],
            "llm_error": llm_error,
        }

        self._tracer.emit(
            request_id,
            "final_response",
            {"used_path": used_path, "metrics": metrics},
        )
        return OrchestratorResult(
            final_text=final_text,
            used_path=used_path,
            fallback_events=fallback_events,
            trace_id=request_id,
            metrics=metrics,
        )

    def _update_router_feedback(
        self,
        expert_name: str,
        status: ExpertStatus,
        elapsed_ms: int,
    ) -> None:
        updater = getattr(self._router, "update_feedback", None)
        if callable(updater):
            updater(expert_name=expert_name, status=status, elapsed_ms=elapsed_ms)

    @staticmethod
    def _safe_fallback_text(user_input: str, llm_error: str | None) -> str:
        reason = llm_error or "unknown_error"
        return (
            "Geçici model erişim hatası oluştu, güvenli fallback yanıtı veriliyor.\n"
            f"İstek özeti: {user_input}\n"
            f"Hata: {reason}"
        )

    def _generate_with_timeout(self, prompt: str, system: str | None) -> str:
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(self._llm.generate, prompt, system, False)
        try:
            return future.result(timeout=self._config.limits.llm_timeout_ms / 1000)
        except TimeoutError as exc:
            future.cancel()
            raise TimeoutError("orchestrator llm timeout") from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)

    def _run_expert_with_retries(
        self,
        request_id: str,
        planner_output: PlannerOutput,
        expert_name: str,
        user_input: str,
        session_context: dict[str, str],
    ) -> ExpertResult:
        result: ExpertResult | None = None
        attempts = self._config.limits.max_retries + 1
        for attempt in range(attempts):
            req = ExpertRequest(
                request_id=request_id,
                task_type=planner_output.task_type,
                intent=planner_output.intent,
                user_input=user_input,
                context=session_context,
                latency_budget_ms=planner_output.latency_budget_ms,
            )
            result = self._invoke_expert(expert_name, req)
            self._tracer.emit(
                request_id,
                "expert_call",
                {
                    "expert": expert_name,
                    "attempt": attempt + 1,
                    "status": result.status.value,
                    "elapsed_ms": result.elapsed_ms,
                    "error_code": result.error_code,
                },
            )
            if result.status == ExpertStatus.OK:
                return result

        assert result is not None
        return result

    def _invoke_expert(self, expert_name: str, request: ExpertRequest) -> ExpertResult:
        expert = self._experts.get(expert_name)
        if expert is None:
            return ExpertResult(
                expert_name=expert_name,
                status=ExpertStatus.ERROR,
                confidence=0.0,
                payload={},
                error_code="EXPERT_NOT_FOUND",
                elapsed_ms=0,
            )

        timeout_s = self._config.limits.expert_timeout_ms / 1000
        started = time.perf_counter()

        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(expert.run, request)
            try:
                result = future.result(timeout=timeout_s)
                elapsed = int((time.perf_counter() - started) * 1000)
                # Force returned elapsed to include orchestration overhead.
                return result.model_copy(update={"elapsed_ms": max(result.elapsed_ms, elapsed)})
            except TimeoutError:
                future.cancel()
                elapsed = int((time.perf_counter() - started) * 1000)
                return ExpertResult(
                    expert_name=expert_name,
                    status=ExpertStatus.TIMEOUT,
                    confidence=0.0,
                    payload={},
                    error_code="TIMEOUT",
                    elapsed_ms=elapsed,
                )
            except Exception as exc:
                elapsed = int((time.perf_counter() - started) * 1000)
                return ExpertResult(
                    expert_name=expert_name,
                    status=ExpertStatus.ERROR,
                    confidence=0.0,
                    payload={},
                    error_code=f"EXCEPTION:{type(exc).__name__}",
                    elapsed_ms=elapsed,
                )

    @staticmethod
    def _build_synthesis_prompt(user_input: str, expert_result: ExpertResult) -> str:
        evidence = json.dumps(expert_result.payload, ensure_ascii=False)
        return (
            "You are BinLiquid response synthesizer. "
            "Use the expert evidence to answer clearly and cite uncertainty when needed.\n"
            f"User input: {user_input}\n"
            f"Expert name: {expert_result.expert_name}\n"
            f"Expert payload JSON: {evidence}"
        )

    @staticmethod
    def _build_adjudication_prompt(
        user_input: str,
        primary: ExpertResult,
        secondary: ExpertResult,
    ) -> str:
        primary_payload = json.dumps(primary.payload, ensure_ascii=False)
        secondary_payload = json.dumps(secondary.payload, ensure_ascii=False)
        return (
            "You are an evidence-first adjudicator.\n"
            "Resolve conflicts between two expert outputs.\n"
            f"User input: {user_input}\n"
            f"Primary expert ({primary.expert_name}): {primary_payload}\n"
            f"Secondary expert ({secondary.expert_name}): {secondary_payload}\n"
            "Respond with a single coherent answer and mention uncertainty explicitly when needed."
        )
