from __future__ import annotations

import hashlib
import inspect
import json
import re
from typing import Any, Protocol

from pydantic import Field, JsonValue, model_validator

from imperaos.artifacts.context import ArtifactContextRequest
from imperaos.artifacts.models import (
    ArtifactDataClass,
    ArtifactModel,
    BoundedId,
    OperationContext,
    canonical_json,
)
from imperaos.artifacts.tools import ArtifactToolRegistry
from imperaos.model_providers.errors import ProviderGenerationError
from imperaos.model_providers.models import DataClass
from imperaos.model_providers.native.types import ProviderRequestedTool

_CONTEXT_SECTION = re.compile(
    r"(?:^|\n)## Governed artifact context request\n(?P<body>.*?)(?=\n\n## |\Z)",
    re.DOTALL,
)


class ArtifactAssistantToolCall(ArtifactModel):
    call_id: BoundedId
    name: BoundedId
    arguments: dict[str, JsonValue]


class ArtifactAssistantProviderResponse(ArtifactModel):
    final_text: str | None = Field(default=None, max_length=100_000)
    tool_call: ArtifactAssistantToolCall | None = None

    @model_validator(mode="after")
    def validate_terminal_or_tool(self) -> ArtifactAssistantProviderResponse:
        if (self.final_text is None) == (self.tool_call is None):
            raise ValueError("assistant provider must return exactly one final text or tool call")
        if self.final_text is not None and not self.final_text.strip():
            raise ValueError("assistant provider final text is empty")
        return self


class ArtifactAssistantProvider(Protocol):
    def complete(
        self,
        messages: tuple[dict[str, object], ...],
        tools: tuple[ProviderRequestedTool, ...],
    ) -> ArtifactAssistantProviderResponse: ...


class ArtifactAssistantTurnResult(ArtifactModel):
    final_text: str = Field(min_length=1, max_length=100_000)
    events: tuple[dict[str, JsonValue], ...]


class CoreLlmArtifactProvider:
    def __init__(self, llm: Any) -> None:
        self._llm = llm
        self._data_class = ArtifactDataClass.PUBLIC

    def bind_data_class(self, data_class: ArtifactDataClass) -> None:
        rank = {
            ArtifactDataClass.PUBLIC: 0,
            ArtifactDataClass.INTERNAL: 1,
            ArtifactDataClass.CONFIDENTIAL: 2,
            ArtifactDataClass.REGULATED: 3,
        }
        if rank[data_class] > rank[self._data_class]:
            self._data_class = data_class

    def complete(
        self,
        messages: tuple[dict[str, object], ...],
        tools: tuple[ProviderRequestedTool, ...],
    ) -> ArtifactAssistantProviderResponse:
        tool_contracts = [tool.model_dump(mode="json") for tool in tools]
        system = (
            "You are a governed artifact planner. Return one strict JSON object only. "
            "Use either {\"finalText\":\"...\"} or "
            "{\"toolCall\":{\"callId\":\"...\",\"name\":\"...\",\"arguments\":{...}}}. "
            "Only the supplied tools are allowed; never invent a tool, apply a proposal, "
            "write an export, execute code, or perform external side effects.\n"
            f"TOOLS={canonical_json(tool_contracts)}"
        )
        generate = self._llm.generate
        parameters = inspect.signature(generate).parameters.values()
        supports_data_classes = any(
            parameter.name == "data_classes"
            or parameter.kind is inspect.Parameter.VAR_KEYWORD
            for parameter in parameters
        )
        if not supports_data_classes and self._data_class is not ArtifactDataClass.PUBLIC:
            raise ProviderGenerationError("PROVIDER_DATA_BOUNDARY_DENIED")
        kwargs: dict[str, object] = {
            "prompt": canonical_json({"messages": messages}),
            "system": system,
            "json_mode": True,
        }
        if supports_data_classes:
            kwargs["data_classes"] = [DataClass(self._data_class.value)]
        raw = generate(**kwargs)
        return ArtifactAssistantProviderResponse.model_validate(json.loads(raw))


class ArtifactAssistantToolLoop:
    def __init__(self, registry: ArtifactToolRegistry, *, max_tool_calls: int = 4) -> None:
        if not 1 <= max_tool_calls <= 8:
            raise ValueError("max_tool_calls must be between 1 and 8")
        self._registry = registry
        self._max_tool_calls = max_tool_calls

    def run(
        self,
        provider: ArtifactAssistantProvider,
        *,
        prompt: str,
        context: OperationContext,
        initial_context: ArtifactContextRequest | dict[str, Any] | None = None,
    ) -> ArtifactAssistantTurnResult:
        messages: list[dict[str, object]] = [{"role": "user", "content": prompt}]
        events: list[dict[str, JsonValue]] = []
        if initial_context is not None:
            request = ArtifactContextRequest.model_validate(initial_context)
            result = self._registry.invoke(
                "artifact.get_context",
                request.model_dump(mode="json", by_alias=True),
                context,
            )
            _bind_result_classification(provider, result)
            self._append_result(
                messages,
                events,
                call_id="context-bootstrap",
                tool_name="artifact.get_context",
                result=result,
            )

        tools = self._registry.provider_tools()
        for _ in range(self._max_tool_calls + 1):
            response = provider.complete(tuple(messages), tools)
            if response.final_text is not None:
                return ArtifactAssistantTurnResult(
                    final_text=response.final_text.strip(),
                    events=tuple(events),
                )
            if len(events) >= self._max_tool_calls + int(initial_context is not None):
                raise ValueError("artifact assistant tool budget exceeded")
            call = response.tool_call
            if call is None:
                raise AssertionError("validated response omitted both terminal forms")
            result = self._registry.invoke(call.name, call.arguments, context)
            _bind_result_classification(provider, result)
            messages.append(
                {
                    "role": "assistant",
                    "toolCall": call.model_dump(mode="json", by_alias=True),
                }
            )
            self._append_result(
                messages,
                events,
                call_id=call.call_id,
                tool_name=call.name,
                result=result,
            )
        raise ValueError("artifact assistant tool budget exceeded")

    @staticmethod
    def _append_result(
        messages: list[dict[str, object]],
        events: list[dict[str, JsonValue]],
        *,
        call_id: str,
        tool_name: str,
        result: ArtifactModel,
    ) -> None:
        payload = result.model_dump(mode="json", by_alias=True)
        messages.append(
            {
                "role": "tool",
                "callId": call_id,
                "name": tool_name,
                "content": canonical_json(payload),
            }
        )
        summary_keys = (
            "status",
            "artifactId",
            "revisionId",
            "revisionNumber",
            "proposalId",
            "approvalId",
            "actionHash",
            "baseRevisionNumber",
            "dataClass",
            "kind",
            "title",
            "summary",
            "reasonCode",
            "projectionSha256",
            "selectionSha256",
        )
        summary: dict[str, JsonValue] = {
            "toolName": tool_name,
            "callId": call_id,
            "resultSha256": hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest(),
        }
        summary.update({key: payload[key] for key in summary_keys if key in payload})
        events.append(summary)


def _bind_result_classification(
    provider: ArtifactAssistantProvider,
    result: ArtifactModel,
) -> None:
    binder = getattr(provider, "bind_data_class", None)
    if not callable(binder):
        return
    payload = result.model_dump(mode="python", by_alias=True)
    value = payload.get("dataClass")
    if value is not None:
        binder(ArtifactDataClass(value))


def extract_artifact_context_request(prompt: str) -> ArtifactContextRequest | None:
    match = _CONTEXT_SECTION.search(prompt)
    if match is None:
        return None
    return ArtifactContextRequest.model_validate_json(match.group("body").strip())
