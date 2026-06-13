from __future__ import annotations

from binliquid.control_plane.provider_conformance import run_provider_native_conformance
from binliquid.control_plane.providers.anthropic_messages import AnthropicMessagesAdapter


def test_anthropic_messages_request_builder_uses_messages_contract_without_raw_persistence(
) -> None:
    adapter = AnthropicMessagesAdapter()
    request = adapter.build_request(
        prompt="Summarize failed jobs and propose remediation.",
        model="claude-3-5-sonnet-latest",
        custom_tools=[{"name": "draft_ticket"}],
    )

    assert request.provider_kind == "anthropic_messages"
    assert request.raw_persistence is False
    assert request.native_payload["messages"][0]["role"] == "user"
    assert request.native_payload["messages"][0]["content"][0]["type"] == "text"
    assert request.native_payload["metadata"]["binliquid_retention"] == "hash_only_store_false"
    assert request.native_payload["tools"][0]["execution_mode"] == "proposal_only"
    assert request.tool_policy.server_tools_policy == "denied"
    assert request.retention_policy.evidence_mode == "hash_only"


def test_anthropic_messages_offline_conformance_passes_without_network(tmp_path) -> None:
    report = run_provider_native_conformance(
        "anthropic_messages",
        profile="enterprise",
        offline=True,
        output_dir=tmp_path,
    )

    assert report.status == "pass"
    assert report.provider_kind == "anthropic_messages"
    assert report.offline is True
    assert report.fixtures_run > 0
    assert report.evidence_path is not None
    assert (tmp_path / "anthropic_messages_conformance.json").exists()
