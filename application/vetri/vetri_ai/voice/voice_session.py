from __future__ import annotations


CHAT_TRIGGERS = ["let's talk", "chat with me", "talk to me"]


def should_route_to_chat(text: str) -> bool:
    lowered = text.lower()
    return any(trigger in lowered for trigger in CHAT_TRIGGERS)
