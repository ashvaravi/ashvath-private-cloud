from __future__ import annotations


def score_memory_value(text: str) -> int:
    lowered = text.lower()
    if any(word in lowered for word in ["preference", "architecture", "incident", "fix", "milestone"]):
        return 8
    return 3
