"""Remove secrets and personal data before anything is logged (ENGINEERING.md section 10)."""

import re
from collections.abc import Mapping, MutableMapping
from typing import Any

REDACTED = "***REDACTED***"

# Key names (case-insensitive substrings) whose values are always hidden.
SENSITIVE_KEY_PARTS: tuple[str, ...] = (
    "token",
    "secret",
    "password",
    "passwd",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "client_id",
    "totp",
    "account_number",
)

# Short names matched only as a whole word (so "span" or "company" are not hidden).
SENSITIVE_KEY_WORDS: frozenset[str] = frozenset({"pan"})
_KEY_WORD_SPLIT = re.compile(r"[^a-z0-9]+")

# Values that look like credentials even under an innocent key.
_SENSITIVE_VALUE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bBearer\s+\S+", re.IGNORECASE),
    re.compile(r"\beyJ[\w-]+\.[\w-]+\.[\w-]+"),  # JWT
)


def is_sensitive_key(key: str) -> bool:
    lowered = key.lower()
    if any(part in lowered for part in SENSITIVE_KEY_PARTS):
        return True
    return not SENSITIVE_KEY_WORDS.isdisjoint(_KEY_WORD_SPLIT.split(lowered))


def redact_value(value: Any) -> Any:  # noqa: ANN401 - log values can be anything
    """Redact credentials inside a value, recursing into dicts, lists and tuples."""
    if isinstance(value, str):
        for pattern in _SENSITIVE_VALUE_PATTERNS:
            value = pattern.sub(REDACTED, value)
        return value
    if isinstance(value, Mapping):
        return redact_mapping(value)
    if isinstance(value, list | tuple):
        return type(value)(redact_value(item) for item in value)
    return value


def redact_mapping(data: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: REDACTED if is_sensitive_key(key) else redact_value(value)
        for key, value in data.items()
    }


def redact_processor(
    _logger: object, _method_name: str, event_dict: MutableMapping[str, Any]
) -> Mapping[str, Any]:
    """structlog processor: run last before rendering, so nothing escapes redaction."""
    return redact_mapping(event_dict)
