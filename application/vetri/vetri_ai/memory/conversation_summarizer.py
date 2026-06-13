from __future__ import annotations


def safe_conversation_summary(text: str) -> dict[str, object]:
    return {"ok": True, "summary": text[:500], "safe_for_memory": "do not remember" not in text.lower()}
