from __future__ import annotations


def select_mode(intent: str, risk: str) -> str:
    if risk == "high":
        return "emergency"
    if intent in {"diagnostic", "mac_export_query"}:
        return "diagnostic"
    if intent in {"architecture_question", "project_status", "memory_query", "spotify_query"}:
        return "chat"
    return "fast"
