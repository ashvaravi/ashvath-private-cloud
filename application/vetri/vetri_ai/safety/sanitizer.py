from __future__ import annotations

import re
from typing import Any


SENSITIVE_PATTERNS = [
    re.compile(r"(?i)(authorization:\s*bearer\s+)[A-Za-z0-9._\-]+"),
    re.compile(r"(?i)(api[_-]?key[\"'\s:=]+)[A-Za-z0-9._\-]+"),
    re.compile(r"(?i)(token[\"'\s:=]+)[A-Za-z0-9._\-]+"),
    re.compile(r"(?i)(password[\"'\s:=]+)[^\s,}]+"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----", re.S),
]


def sanitize_text(text: str, max_length: int = 4000) -> str:
    clean = text
    for pattern in SENSITIVE_PATTERNS:
        clean = pattern.sub(lambda match: match.group(1) + "[REDACTED]" if match.groups() else "[REDACTED_PRIVATE_KEY]", clean)
    if ".env" in clean.lower():
        clean = clean.replace(".env", "[ENV_FILE]")
    if len(clean) > max_length:
        clean = clean[:max_length] + "...[TRUNCATED]"
    return clean


def sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(marker in lowered for marker in ["token", "password", "secret", "api_key", "authorization", "private_key"]):
                result[key] = "[REDACTED]"
            else:
                result[key] = sanitize_value(item)
        return result
    if isinstance(value, list):
        return [sanitize_value(item) for item in value[:100]]
    if isinstance(value, str):
        return sanitize_text(value)
    return value
