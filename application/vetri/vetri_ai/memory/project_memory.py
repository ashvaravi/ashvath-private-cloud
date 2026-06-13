from __future__ import annotations

from vetri_ai.memory.memory_manager import MemoryManager


def load_project_summary() -> dict[str, object]:
    return {"recent_project_events": MemoryManager().get_recent_events(20)}
