from __future__ import annotations

import re

SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_-]{8,}"),
    re.compile(r"ghp_[A-Za-z0-9_]{8,}"),
    re.compile(r"(?i)(api[_-]?key|token|password|secret|bearer)\s*[:=]\s*['\"]?[^'\"\s]{4,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
)

SENSITIVE_KEYS = {
    "api_key",
    "token",
    "password",
    "secret",
    "bearer",
    "private_key",
    "credential",
}


def redact_text(value: str) -> str:
    redacted = value
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub("[redacted-secret]", redacted)
    return redacted.strip()


def contains_secret_marker(value: str) -> bool:
    return redact_text(value) != value.strip()


def has_sensitive_key(value: object) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            lowered = str(key).lower()
            if any(marker in lowered for marker in SENSITIVE_KEYS):
                return True
            if has_sensitive_key(nested):
                return True
    if isinstance(value, list):
        return any(has_sensitive_key(item) for item in value)
    return False
