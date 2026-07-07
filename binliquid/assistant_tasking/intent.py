from __future__ import annotations

import re
import unicodedata

from binliquid.assistant_tasking.models import (
    AssistantTaskIntentKind,
    AssistantTaskRiskClass,
)


def normalize_message(value: str) -> str:
    lowered = value.strip().lower().replace("ı", "i")
    simplified = "".join(
        char for char in unicodedata.normalize("NFKD", lowered) if not unicodedata.combining(char)
    )
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9_.:/@-]+", " ", simplified)).strip()


def classify_intent(message: str) -> AssistantTaskIntentKind:
    normalized = normalize_message(message)
    if any(term in normalized for term in ("nereden biliyorsun", "source", "kaynak")):
        return AssistantTaskIntentKind.EXPLAIN_RUN
    if any(term in normalized for term in ("nasil", "how to", "ne ise yarar")):
        return AssistantTaskIntentKind.ASK_HOW_TO
    if any(term in normalized for term in ("sil", "delete", "drop", "wipe", "yok et")):
        return AssistantTaskIntentKind.UNSUPPORTED_DESTRUCTIVE
    if any(term in normalized for term in ("gorev", "task", "agent", "ajan", "ticket", "uyari")):
        return AssistantTaskIntentKind.PLAN_AGENT_TASK
    return AssistantTaskIntentKind.CLARIFICATION_REQUIRED


def classify_risk(message: str) -> AssistantTaskRiskClass:
    normalized = normalize_message(message)
    if any(term in normalized for term in ("api key", "token", "password", "sifre", "credential")):
        return AssistantTaskRiskClass.CREDENTIAL_SENSITIVE
    if any(term in normalized for term in ("sil", "delete", "drop", "wipe", "yok et")):
        return AssistantTaskRiskClass.DESTRUCTIVE
    if any(term in normalized for term in ("policy", "yok say", "ignore", "approval gerekmeden")):
        return AssistantTaskRiskClass.MUTATION
    if any(term in normalized for term in ("ticket", "acsin", "aç", "create", "update")):
        return AssistantTaskRiskClass.EXTERNAL_WRITE
    if any(term in normalized for term in ("incele", "oku", "read", "inspect", "triage", "uyari")):
        return AssistantTaskRiskClass.READ_ONLY
    return AssistantTaskRiskClass.UNKNOWN


def extract_agent_hint(message: str) -> str | None:
    normalized = normalize_message(message)
    if "bilinmeyen-agent" in normalized or "unknown-agent" in normalized:
        return "unknown-agent"
    if "external gateway" in normalized or "external agent" in normalized:
        return "external-agent"
    if "unenrolled" in normalized or "enrolled olmayan" in normalized:
        return "external-agent"
    if "governed ops" in normalized:
        return "external-agent"
    return None
