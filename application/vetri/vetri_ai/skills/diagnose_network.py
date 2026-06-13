from __future__ import annotations

from vetri_ai.skills.mac_export_summary import _load_export


def run() -> dict[str, object]:
    summary = _load_export("latest_network_summary.json")
    if not summary:
        return {"status": "missing_data", "evidence": ["latest_network_summary.json missing"], "likely_cause": "Mac exports are not synced.", "safe_next_step": "Run scripts\\sync_from_mac.ps1.", "confidence": 0.4}
    data = summary.get("data", {})
    ports = data.get("known_ports", {}) if isinstance(data.get("known_ports"), dict) else {}
    closed = [name for name, open_ in ports.items() if not open_]
    tailscale = data.get("tailscale_ipv4_available")
    return {
        "status": "healthy_with_warning" if not closed else "needs_attention",
        "evidence": [f"open_ports={len(ports) - len(closed)}/{len(ports)}", f"closed_ports={closed}", f"tailscale_ipv4_available={tailscale}", "auth_required is expected for protected backend endpoint"],
        "likely_cause": "Tailscale IPv4 is missing in export." if not tailscale else "No issue detected in latest network metadata.",
        "safe_next_step": "If remote access fails, check Tailscale app status on Windows and Mac; do not edit ACLs automatically.",
        "confidence": 0.82
    }
