from __future__ import annotations

from vetri_ai.memory.memory_store import MemoryStore


def review_personal_memory() -> str:
    return MemoryStore().summarize_review()
