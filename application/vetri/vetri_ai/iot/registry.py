from __future__ import annotations

from pathlib import Path
from typing import Any

from vetri_ai.settings import ROOT_DIR
from vetri_ai.utils.json_utils import load_json


def load_registry(root: Path = ROOT_DIR) -> dict[str, Any]:
    data = load_json(root / "config" / "iot_registry.json", default={})
    return data if isinstance(data, dict) else {}


def format_registry() -> str:
    registry = load_registry()
    devices = registry.get("devices", {})
    groups = registry.get("groups", {})
    lines = ["IoT registry:", f"- Control route: {registry.get('control_route')}", f"- Devices: {len(devices)}", f"- Groups: {', '.join(groups.keys())}"]
    for entity, meta in devices.items():
        if isinstance(meta, dict):
            lines.append(f"- {meta.get('name', entity)} ({entity}) room={meta.get('room')} capabilities={', '.join(meta.get('capabilities', []))}")
    return "\n".join(lines)


def devices_in_room(room: str) -> str:
    registry = load_registry()
    devices = registry.get("devices", {})
    matches = []
    for entity, meta in devices.items():
        if isinstance(meta, dict) and meta.get("room") == room:
            matches.append(f"- {meta.get('name', entity)} ({entity})")
    if not matches:
        return f"I do not have devices registered for {room}."
    return f"Devices in {room}:\n" + "\n".join(matches)
