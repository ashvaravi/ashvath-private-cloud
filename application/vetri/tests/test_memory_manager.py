from vetri_ai.memory.memory_manager import MemoryManager


def test_memory_summary_loads():
    summary = MemoryManager().load_memory_summary()
    assert "recent_project_events" in summary
