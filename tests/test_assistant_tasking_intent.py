from __future__ import annotations

from binliquid.assistant_tasking.intent import classify_intent, classify_risk, extract_agent_hint


def test_intent_classifies_tasking_and_destructive_prompts() -> None:
    assert (
        classify_intent("Governed ops agent'e uyarilari inceleme gorevi ver")
        == "plan_agent_task"
    )
    assert classify_risk("son servis uyarilarini incele") == "read_only"
    assert classify_risk("takip ticket'i acsin") == "external_write"
    assert classify_intent("eski kayitlari sil") == "unsupported_destructive"
    assert classify_risk("api key ile oku") == "credential_sensitive"


def test_intent_extracts_agent_hints() -> None:
    assert extract_agent_hint("Bilinmeyen-agent'a gorev ver") == "unknown-agent"
    assert extract_agent_hint("Enrolled olmayan external agent ile oku") == "external-agent"
