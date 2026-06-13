from __future__ import annotations

from vetri_ai.iot.registry import load_registry


def plan_iot_action(text: str) -> str:
    lowered = text.lower()
    registry = load_registry()
    if "all devices" in lowered:
        return (
            "Blocked broad IoT plan: 'all devices' is too broad to execute blindly. "
            "Vetri would need a narrower room/group target, explicit confirmation, Mac backend verified endpoint routing, and post-action verification."
        )
    if "bedroom" in lowered and "light" in lowered:
        group = registry.get("groups", {}).get("bedroom_lights", {})
        entities = group.get("entities", [])
        steps = [
            "Classify request as medium risk Home Assistant group control.",
            "Require explicit confirmation before execution.",
            "Route only to Mac backend POST /api/v1/home/control/group/verified.",
            "Target group bedroom_lights with entities: " + ", ".join(entities),
            "Backend verifies final state; Windows does not call Home Assistant directly."
        ]
        return "Safe IoT control plan:\n" + "\n".join(f"- {step}" for step in steps)
    return "I can plan IoT actions for registered rooms/groups, but I will not execute control from chat without confirmation and backend verification."
