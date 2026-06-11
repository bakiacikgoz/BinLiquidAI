from __future__ import annotations

from pathlib import Path

from binliquid.model_providers.native.types import (
    OpenAIResponsesRequest,
    OpenAIResponsesResult,
    ProviderNativeConformanceReport,
    ProviderStoragePolicy,
    ProviderToolPolicyDecision,
    ProviderToolProposal,
)


def test_native_contract_schemas_are_generated() -> None:
    expected = [
        "openai_responses_request.schema.json",
        "openai_responses_result.schema.json",
        "provider_storage_policy.schema.json",
        "provider_tool_policy_decision.schema.json",
        "provider_tool_proposal.schema.json",
        "provider_native_conformance_report.schema.json",
    ]

    for name in expected:
        assert Path("contracts/model_providers", name).exists()


def test_native_contract_models_forbid_raw_payload_defaults() -> None:
    storage = ProviderStoragePolicy(provider_id="openai-responses-preview")
    assert storage.request_store_flag is False
    assert storage.raw_payload_persistence is False

    assert OpenAIResponsesRequest
    assert OpenAIResponsesResult
    assert ProviderToolPolicyDecision
    assert ProviderToolProposal
    assert ProviderNativeConformanceReport
