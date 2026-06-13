from __future__ import annotations

from typing import Any

from vetri_ai.safety.sanitizer import sanitize_value


def build_context_packet(
    current_request: str,
    latest_status_summary: dict[str, Any] | None = None,
    recent_clean_events: list[dict[str, Any]] | None = None,
    relevant_memory: list[dict[str, Any]] | None = None,
    allowed_actions: list[str] | None = None,
) -> dict[str, Any]:
    packet = {
        "system_name": "Vetri",
        "mode": "reasoning",
        "current_request": current_request,
        "user_profile": {
            "preferred_name": "Ashvath",
            "style": "technical, clear, step-by-step"
        },
        "server_profile": {
            "execution_server": "MacBook Pro 2016",
            "ai_brain": "Windows PC",
            "project_root": "~/Ashvath-private-cloud",
            "services": [
                "Immich",
                "Home Assistant",
                "Uptime Kuma",
                "Netdata",
                "Portainer",
                "Vetri Backend",
                "Vetri Frontend"
            ]
        },
        "latest_status_summary": latest_status_summary or {},
        "recent_clean_events": recent_clean_events or [],
        "relevant_memory": relevant_memory or [],
        "allowed_actions": allowed_actions or [],
        "privacy_rules": [
            "No secrets included.",
            "No raw logs included.",
            "No photos or videos included.",
            "LLM cannot execute commands."
        ]
    }
    return sanitize_value(packet)


class ContextPacketBuilder:
    def build_from_result(self, mode: str, user_request: str, vetri_result: dict[str, Any], allowed_actions: list[str] | None = None) -> dict[str, Any]:
        packet = build_context_packet(user_request, latest_status_summary={"mode": mode}, relevant_memory=[vetri_result], allowed_actions=allowed_actions)
        packet["mode"] = mode
        return packet
