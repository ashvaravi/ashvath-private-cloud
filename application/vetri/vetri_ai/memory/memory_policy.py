from __future__ import annotations


SECRET_MARKERS = ["api key", "apikey", "password", "token", ".env", "secret", "private key", "database dump"]


def can_store_memory(text: str) -> tuple[bool, str]:
    lowered = text.lower()
    if "do not remember" in lowered:
        return False, "User explicitly said do not remember."
    for marker in SECRET_MARKERS:
        if marker in lowered:
            return False, f"Memory contains excluded secret marker: {marker}"
    return True, "Allowed safe memory."


def importance_for(text: str) -> str:
    lowered = text.lower()
    if "always" in lowered or "safety" in lowered or "architecture" in lowered:
        return "high"
    if "prefer" in lowered or "remember" in lowered:
        return "medium"
    return "low"
