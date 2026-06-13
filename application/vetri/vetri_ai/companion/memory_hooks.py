from __future__ import annotations

from vetri_ai.memory.memory_store import MemoryStore


def remember_if_explicit(text: str) -> dict[str, object] | None:
    lowered = text.lower()
    if lowered.startswith("remember that") or " remember that " in lowered:
        return MemoryStore().remember(text, source="companion_explicit")
    return None
