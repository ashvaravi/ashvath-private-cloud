from __future__ import annotations

from vetri_ai.skills.mac_export_summary import _load_export


def run() -> dict[str, object]:
    services = _load_export("latest_service_summary.json")
    network = _load_export("latest_network_summary.json")
    if not services and not network:
        return {"status": "missing_data", "evidence": ["latest_service_summary.json and latest_network_summary.json missing"], "likely_cause": "Mac exports are not synced.", "safe_next_step": "Run scripts\\sync_from_mac.ps1.", "confidence": 0.4}
    ports = {}
    if network:
        ports.update(network.get("data", {}).get("known_ports", {}))
    if services:
        ports.update(services.get("data", {}).get("known_ports", {}))
    immich_open = ports.get("immich_2283")
    return {
        "status": "healthy" if immich_open else "needs_attention",
        "evidence": [f"immich_2283 open={immich_open}", "Diagnosis is read-only export based."],
        "likely_cause": "No issue detected in latest Immich port metadata." if immich_open else "Immich port 2283 may be closed or missing from export.",
        "safe_next_step": "Check latest service summary and backup summary; do not restart containers automatically.",
        "confidence": 0.76
    }
