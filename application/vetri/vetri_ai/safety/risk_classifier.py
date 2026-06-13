from __future__ import annotations


def classify_risk(intent: str) -> str:
    if intent == "home_control":
        return "medium"
    if intent == "unsafe":
        return "high"
    if intent in {"backup_status", "storage_status", "network_status", "diagnostic", "mac_export_query", "spotify_query"}:
        return "low"
    return "none"
