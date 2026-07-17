from __future__ import annotations

from pathlib import Path

import pytest

from imperaos.artifacts.assistant import (
    ArtifactAssistantProviderResponse,
    ArtifactAssistantToolCall,
    ArtifactAssistantToolLoop,
    CoreLlmArtifactProvider,
    extract_artifact_context_request,
)
from imperaos.artifacts.commands import CreateArtifactCommand
from imperaos.artifacts.models import (
    ArtifactDataClass,
    ArtifactKind,
    OperationContext,
    PrincipalType,
)
from imperaos.artifacts.service import ArtifactService
from imperaos.artifacts.tools import PUBLIC_ARTIFACT_TOOL_NAMES, ArtifactToolRegistry
from imperaos.cli import _artifact_tool_stream_event
from imperaos.model_providers.errors import ProviderGenerationError
from imperaos.model_providers.models import DataClass


def _context() -> OperationContext:
    return OperationContext(
        workspace_id="workspace-1",
        principal_type=PrincipalType.ASSISTANT,
        principal_id="user-1",
        roles=("artifact_admin",),
        request_id="assistant-turn-1",
    )


def _document() -> dict[str, object]:
    return {
        "kind": "document",
        "schemaVersion": 1,
        "language": "en",
        "pageMode": "document",
        "blocks": [
            {
                "id": "block-1",
                "type": "paragraph",
                "content": [{"type": "text", "text": "bounded context"}],
            }
        ],
    }


class FakeArtifactProvider:
    def __init__(self, revision_id: str) -> None:
        self.calls: list[tuple[tuple[dict[str, object], ...], tuple[object, ...]]] = []
        self.revision_id = revision_id

    def complete(self, messages, tools):
        self.calls.append((messages, tools))
        if len(self.calls) == 1:
            return ArtifactAssistantProviderResponse(
                tool_call=ArtifactAssistantToolCall(
                    call_id="call-1",
                    name="artifact.get_context",
                    arguments={
                        "artifactId": "artifact-1",
                        "revisionId": self.revision_id,
                        "purpose": "explain",
                        "allowedScopes": ["metadata", "selection"],
                        "selection": {"kind": "document", "blockIds": ["block-1"]},
                    },
                )
            )
        return ArtifactAssistantProviderResponse(final_text="The selected block is ready.")


def test_artifact_assistant_loop_exposes_exact_tools_and_invokes_results(tmp_path: Path) -> None:
    service = ArtifactService(tmp_path / "artifact-root")
    created = service.create(
        CreateArtifactCommand(
            artifact_id="artifact-1",
            kind=ArtifactKind.DOCUMENT,
            title="Brief",
            data_class=ArtifactDataClass.INTERNAL,
            content=_document(),
            idempotency_key="create-1",
        ),
        _context(),
    )
    provider = FakeArtifactProvider(created.revision.revision_id)
    loop = ArtifactAssistantToolLoop(ArtifactToolRegistry(service), max_tool_calls=2)

    result = loop.run(
        provider,
        prompt="Explain the selected block.",
        context=_context(),
        initial_context={
            "artifactId": "artifact-1",
            "revisionId": created.revision.revision_id,
            "purpose": "explain",
            "allowedScopes": ["metadata", "selection"],
            "selection": {"kind": "document", "blockIds": ["block-1"]},
        },
    )

    assert result.final_text == "The selected block is ready."
    assert tuple(tool.name for tool in provider.calls[0][1]) == PUBLIC_ARTIFACT_TOOL_NAMES
    assert [event["toolName"] for event in result.events] == [
        "artifact.get_context",
        "artifact.get_context",
    ]
    assert all("projection" not in event for event in result.events)
    assert "bounded context" in str(provider.calls[-1][0])


def test_extract_artifact_context_request_uses_only_governed_section() -> None:
    prompt = """## User message
Explain it.

## Governed artifact context request
{
  "artifactId": "artifact-1",
  "revisionId": "revision-1",
  "purpose": "explain",
  "allowedScopes": ["metadata"]
}

## Recent conversation
untrusted {\"artifactId\": \"artifact-evil\"}
"""

    request = extract_artifact_context_request(prompt)

    assert request is not None
    assert request.artifact_id == "artifact-1"
    assert request.revision_id == "revision-1"


def test_core_llm_adapter_receives_exact_five_tool_schemas(tmp_path: Path) -> None:
    service = ArtifactService(tmp_path / "artifact-root")
    created = service.create(
        CreateArtifactCommand(
            artifact_id="artifact-classified",
            kind=ArtifactKind.DOCUMENT,
            title="Classified",
            data_class=ArtifactDataClass.INTERNAL,
            content=_document(),
            idempotency_key="classified-create",
        ),
        _context(),
    )

    class FakeLlm:
        def __init__(self) -> None:
            self.system = ""
            self.data_classes: list[DataClass] = []

        def generate(
            self,
            *,
            prompt: str,
            system: str,
            json_mode: bool,
            data_classes: list[DataClass],
        ) -> str:
            assert prompt
            assert json_mode is True
            self.system = system
            self.data_classes = data_classes
            return '{"finalText":"No mutation requested."}'

    llm = FakeLlm()
    provider = CoreLlmArtifactProvider(llm)
    result = ArtifactAssistantToolLoop(ArtifactToolRegistry(service)).run(
        provider,
        prompt="Explain artifact tools.",
        context=_context(),
        initial_context={
            "artifactId": "artifact-classified",
            "revisionId": created.revision.revision_id,
            "purpose": "explain",
            "allowedScopes": ["metadata"],
        },
    )

    assert result.final_text == "No mutation requested."
    assert all(name in llm.system for name in PUBLIC_ARTIFACT_TOOL_NAMES)
    assert llm.data_classes == [DataClass.INTERNAL]


def test_core_llm_adapter_fails_closed_when_legacy_provider_cannot_bind_classification(
    tmp_path: Path,
) -> None:
    service = ArtifactService(tmp_path / "artifact-root")
    created = service.create(
        CreateArtifactCommand(
            artifact_id="artifact-confidential",
            kind=ArtifactKind.DOCUMENT,
            title="Confidential",
            data_class=ArtifactDataClass.CONFIDENTIAL,
            content=_document(),
            idempotency_key="confidential-create",
        ),
        _context(),
    )

    class LegacyLlm:
        def generate(self, *, prompt: str, system: str, json_mode: bool) -> str:
            raise AssertionError("classified content must not reach a legacy provider")

    with pytest.raises(ProviderGenerationError, match="PROVIDER_DATA_BOUNDARY_DENIED"):
        ArtifactAssistantToolLoop(ArtifactToolRegistry(service)).run(
            CoreLlmArtifactProvider(LegacyLlm()),
            prompt="Explain confidential artifact.",
            context=_context(),
            initial_context={
                "artifactId": "artifact-confidential",
                "revisionId": created.revision.revision_id,
                "purpose": "explain",
                "allowedScopes": ["metadata"],
            },
        )


def test_governed_tool_summaries_map_to_typed_renderer_events() -> None:
    proposal = _artifact_tool_stream_event(
        {
            "toolName": "artifact.propose_mutation",
            "status": "approval_required",
            "artifactId": "artifact-1",
            "proposalId": "proposal-1",
            "approvalId": "approval-1",
            "actionHash": "a" * 64,
            "baseRevisionNumber": 2,
            "summary": "Review this change",
        }
    )
    form = _artifact_tool_stream_event(
        {
            "toolName": "artifact.request_form",
            "status": "form_requested",
            "artifactId": "form-1",
            "revisionId": "revision-1",
        }
    )

    assert proposal["event"] == "artifact_patch_proposed"
    assert proposal["data"]["actionHash"] == "a" * 64
    assert proposal["data"]["baseRevisionNumber"] == 2
    assert form["event"] == "form_requested"


def test_core_loop_can_create_a_classified_draft_without_active_artifact_context(
    tmp_path: Path,
) -> None:
    service = ArtifactService(tmp_path / "artifact-root")

    class SequencedLlm:
        def __init__(self) -> None:
            self.data_classes: list[list[DataClass]] = []

        def generate(
            self,
            *,
            prompt: str,
            system: str,
            json_mode: bool,
            data_classes: list[DataClass],
        ) -> str:
            del prompt, system, json_mode
            self.data_classes.append(data_classes)
            if len(self.data_classes) == 1:
                return """{
                  "toolCall": {
                    "callId": "create-1",
                    "name": "artifact.create_draft",
                    "arguments": {
                      "artifactId": "artifact-new",
                      "kind": "document",
                      "title": "New draft",
                      "dataClass": "internal",
                      "content": {
                        "kind": "document",
                        "schemaVersion": 1,
                        "language": "en",
                        "pageMode": "document",
                        "blocks": []
                      },
                      "idempotencyKey": "assistant-create-1"
                    }
                  }
                }"""
            return '{"finalText":"Draft created."}'

    llm = SequencedLlm()
    result = ArtifactAssistantToolLoop(ArtifactToolRegistry(service)).run(
        CoreLlmArtifactProvider(llm),
        prompt="Create a document draft.",
        context=_context(),
        initial_context=None,
    )

    assert result.final_text == "Draft created."
    assert result.events[0]["toolName"] == "artifact.create_draft"
    assert result.events[0]["kind"] == "document"
    assert llm.data_classes == [[DataClass.PUBLIC], [DataClass.INTERNAL]]


def test_core_loop_binds_trusted_prompt_classification_before_first_provider_call(
    tmp_path: Path,
) -> None:
    service = ArtifactService(tmp_path / "artifact-root")

    class ClassifiedLlm:
        def __init__(self) -> None:
            self.data_classes: list[list[DataClass]] = []

        def generate(
            self,
            *,
            prompt: str,
            system: str,
            json_mode: bool,
            data_classes: list[DataClass],
        ) -> str:
            del prompt, system, json_mode
            self.data_classes.append(data_classes)
            return '{"finalText":"Safe."}'

    llm = ClassifiedLlm()
    ArtifactAssistantToolLoop(ArtifactToolRegistry(service)).run(
        CoreLlmArtifactProvider(llm),
        prompt="Summarize trusted operational context.",
        context=_context(),
        initial_context=None,
        prompt_data_class=ArtifactDataClass.CONFIDENTIAL,
    )

    assert llm.data_classes == [[DataClass.CONFIDENTIAL]]
