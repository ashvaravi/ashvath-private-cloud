from __future__ import annotations

from vetri_ai.memory.memory_manager import MemoryManager


def remember_preference(text: str) -> dict[str, object]:
    return MemoryManager().update_user_preference(text)
