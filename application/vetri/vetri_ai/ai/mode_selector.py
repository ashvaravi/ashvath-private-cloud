from __future__ import annotations


def select_ai_mode(text: str) -> str:
    lowered = text.lower()
    if "diagnose" in lowered:
        return "local_diagnosis"
    if "remember" in lowered or "memory" in lowered:
        return "local_memory"
    if "plan" in lowered:
        return "action_planning_no_execute"
    if "friend" in lowered or "talk to me" in lowered or "deeper explanation" in lowered:
        return "openai_reasoning"
    return "local_fast"
