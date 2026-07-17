from __future__ import annotations

from pathlib import Path

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

    class FakeLlm:
        def __init__(self) -> None:
            self.system = ""

        def generate(self, *, prompt: str, system: str, json_mode: bool) -> str:
            assert prompt
            assert json_mode is True
            self.system = system
            return '{"finalText":"No mutation requested."}'

    llm = FakeLlm()
    provider = CoreLlmArtifactProvider(llm)
    result = ArtifactAssistantToolLoop(ArtifactToolRegistry(service)).run(
        provider,
        prompt="Explain artifact tools.",
        context=_context(),
    )

    assert result.final_text == "No mutation requested."
    assert all(name in llm.system for name in PUBLIC_ARTIFACT_TOOL_NAMES)
