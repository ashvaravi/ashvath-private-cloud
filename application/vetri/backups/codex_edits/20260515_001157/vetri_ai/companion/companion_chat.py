from __future__ import annotations

from vetri_ai.ai.openai_reasoner import reason_with_openai_or_fallback
from vetri_ai.memory.memory_store import MemoryStore
from vetri_ai.utils.json_utils import load_json
from vetri_ai.settings import ROOT_DIR


def companion_response(text: str) -> str:
    lowered = text.lower()
    store = MemoryStore()
    if "what do you remember" in lowered or "how i like to work" in lowered:
        return store.summarize_review()
    if "how am i doing" in lowered or "project is going" in lowered or "talk to me like a friend" in lowered or "just talk to me" in lowered:
        daily = load_json(ROOT_DIR / "data" / "daily_summaries" / "latest_daily_summary.json", default={})
        milestones = daily.get("milestones", []) if isinstance(daily, dict) else []
        memory = store.review(limit=5)
        memory_bits = "; ".join(str(item.get("text")) for item in memory[-3:])
        local = (
            "You are doing this the right way: you locked the stable voice and Mac backend foundations first, then added Windows brain capabilities behind feature flags and safety routing. "
            f"Latest project memory says: {'; '.join(milestones[-3:]) if milestones else 'a fresh daily summary may be needed'}. "
            f"I remember these working preferences: {memory_bits if memory_bits else 'no rich personal preferences saved yet'}."
        )
        reasoned = reason_with_openai_or_fallback(text, relevant_memory=memory)
        if reasoned.get("used_openai"):
            return str(reasoned.get("response"))
        return local + " " + str(reasoned.get("response", ""))
    return str(reason_with_openai_or_fallback(text, relevant_memory=store.review(limit=5)).get("response"))
