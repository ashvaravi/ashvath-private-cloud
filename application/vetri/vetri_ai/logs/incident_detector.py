from __future__ import annotations


def detect_incidents(status: dict[str, object]) -> list[dict[str, object]]:
    text = str(status).lower()
    rules = {
        "backend_unreachable": ["backend", "unreachable"],
        "frontend_unreachable": ["frontend", "unreachable"],
        "old_backup": ["backup", "old"],
        "disk_usage_high": ["disk", "high"],
        "home_assistant_unreachable": ["home assistant", "unreachable"],
        "immich_degraded": ["immich", "degraded"],
        "tailscale_unreachable": ["tailscale", "unreachable"],
        "export_validation_failure": ["export", "fail"]
    }
    incidents = []
    for name, terms in rules.items():
        if all(term in text for term in terms):
            incidents.append({"rule": name, "status": "detected"})
    return incidents
