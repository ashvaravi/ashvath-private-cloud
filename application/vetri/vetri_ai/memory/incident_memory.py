from __future__ import annotations

from vetri_ai.memory.memory_manager import MemoryManager


def save_incident(incident: dict[str, object]) -> None:
    MemoryManager().save_incident(incident)
