from __future__ import annotations

import pytest

from binliquid.model_providers.errors import ProviderPolicyError, ProviderSchemaError
from binliquid.model_providers.models import (
    ChatMessage,
    DataClass,
    ModelProviderRecord,
    ProviderCallRequest,
    ProviderKind,
    ProviderPolicy,
)
from binliquid.model_providers.native.anthropic_messages import (
    build_anthropic_messages_payload,
    normalize_anthropic_messages_result,
)
from binliquid.model_providers.native.types import (
    ProviderRequestedTool,
    ProviderRequestedToolType,
    ProviderStoragePolicy,
)


def _provider() -> ModelProviderRecord:
    return ModelProviderRecord(
        provider_id="anthropic-messages-preview",
        kind=ProviderKind.ANTHROPIC_MESSAGES,
        enabled=False,
        base_url="https://api.anthropic.com",
        api_key_env="ANTHROPIC_API_KEY",
        auth_mode="custom_header_env",
        default_model="claude-sonnet-4-6",
        data_boundary="public_cloud",
    )


def _policy() -> ProviderPolicy:
    return ProviderPolicy(
        provider_id="anthropic-messages-preview",
        allowed_data_classes=[DataClass.PUBLIC],
        allow_tool_calls=True,
        requires_approval_for_tool_calls=True,
        max_output_tokens=256,
    )


def _request() -> ProviderCallRequest:
    return ProviderCallRequest(
        call_id="call-native",
        run_id="run-native",
        provider_id="anthropic-messages-preview",
        model="claude-sonnet-4-6",
        messages=[ChatMessage(role="user", content="public fixture")],
        data_classes=[DataClass.PUBLIC],
    )


def test_anthropic_messages_payload_is_hash_only_and_canary_only() -> None:
    native = build_anthropic_messages_payload(
        provider=_provider(),
        policy=_policy(),
        request=_request(),
    )

    assert native.payload["model"] == "claude-sonnet-4-6"
    assert native.payload["tool_choice"] == {"type": "none"}
    assert native.canary_only is True
    assert native.live_canary_attempted is False
    assert native.raw_payload_persisted is False
    assert native.request_hash.startswith("sha256:")


def test_anthropic_messages_rejects_raw_payload_persistence() -> None:
    with pytest.raises(
        ProviderPolicyError,
        match="ANTHROPIC_MESSAGES_RAW_PAYLOAD_PERSISTENCE_REJECTED",
    ):
        build_anthropic_messages_payload(
            provider=_provider(),
            policy=_policy(),
            request=_request(),
            storage_policy=ProviderStoragePolicy(
                provider_id="anthropic-messages-preview",
                raw_payload_persistence=True,
            ),
        )


def test_anthropic_messages_denies_server_tools() -> None:
    with pytest.raises(
        ProviderPolicyError,
        match="ANTHROPIC_SERVER_WEB_SEARCH_DEFAULT_DENY",
    ):
        build_anthropic_messages_payload(
            provider=_provider(),
            policy=_policy(),
            request=_request(),
            requested_tools=[
                ProviderRequestedTool(
                    tool_type=ProviderRequestedToolType.BUILTIN_WEB_SEARCH,
                    name="web_search",
                )
            ],
        )


def test_anthropic_messages_allows_client_tool_proposal_only() -> None:
    native = build_anthropic_messages_payload(
        provider=_provider(),
        policy=_policy(),
        request=_request(),
        requested_tools=[
            ProviderRequestedTool(
                tool_type=ProviderRequestedToolType.CUSTOM_FUNCTION,
                name="lookup_public_status",
                parameters={
                    "type": "object",
                    "properties": {"service": {"type": "string"}},
                    "required": ["service"],
                },
            )
        ],
    )

    assert native.payload["tools"][0]["name"] == "lookup_public_status"
    assert native.payload["tool_choice"] == {"type": "auto"}
    assert native.tool_policy_decisions[0].execution_allowed is False
    assert native.tool_policy_decisions[0].proposal_allowed is True


def test_anthropic_messages_normalizes_text_and_tool_use() -> None:
    native = build_anthropic_messages_payload(
        provider=_provider(),
        policy=_policy(),
        request=_request(),
    )

    text_result = normalize_anthropic_messages_result(
        request=native,
        provider_response={
            "type": "message",
            "model": "claude-sonnet-4-6",
            "stop_reason": "end_turn",
            "content": [{"type": "text", "text": "Fixture complete."}],
            "usage": {"input_tokens": 4, "output_tokens": 2},
        },
    )
    tool_result = normalize_anthropic_messages_result(
        request=native,
        provider_response={
            "type": "message",
            "model": "claude-sonnet-4-6",
            "stop_reason": "tool_use",
            "content": [
                {
                    "type": "tool_use",
                    "id": "toolu_fixture",
                    "name": "lookup_public_status",
                    "input": {"service": "operator-panel"},
                }
            ],
        },
    )

    assert text_result.output_text_hash is not None
    assert text_result.usage == {"input_tokens": 4, "output_tokens": 2}
    assert tool_result.tool_proposals[0].tool_name == "lookup_public_status"
    assert tool_result.tool_proposals[0].provider_tool_id == "toolu_fixture"
    assert tool_result.tool_proposals[0].execution_mode == "proposal_only"


def test_anthropic_messages_blocks_pause_and_unknown_blocks() -> None:
    native = build_anthropic_messages_payload(
        provider=_provider(),
        policy=_policy(),
        request=_request(),
    )

    with pytest.raises(ProviderPolicyError, match="ANTHROPIC_MESSAGES_PAUSE_TURN_BLOCKED"):
        normalize_anthropic_messages_result(
            request=native,
            provider_response={
                "type": "message",
                "model": "claude-sonnet-4-6",
                "stop_reason": "pause_turn",
                "content": [{"type": "text", "text": "Paused."}],
            },
        )

    with pytest.raises(ProviderSchemaError, match="ANTHROPIC_MESSAGES_UNSUPPORTED_CONTENT_BLOCK"):
        normalize_anthropic_messages_result(
            request=native,
            provider_response={
                "type": "message",
                "model": "claude-sonnet-4-6",
                "stop_reason": "end_turn",
                "content": [{"type": "thinking", "text": "unsupported"}],
            },
        )
