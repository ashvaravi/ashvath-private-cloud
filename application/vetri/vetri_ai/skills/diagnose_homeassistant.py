from __future__ import annotations

from vetri_ai.skills.mac_export_summary import _load_export


def run() -> dict[str, object]:
    summary = _load_export("latest_homeassistant_summary.json")
    if not summary:
        return {"status": "missing_data", "evidence": ["latest_homeassistant_summary.json missing"], "likely_cause": "Mac exports are not synced.", "safe_next_step": "Run scripts\\sync_from_mac.ps1.", "confidence": 0.4}
    data = summary.get("data", {})
    reachable = data.get("reachable")
    return {
        "status": "healthy" if reachable else "needs_attention",
        "evidence": [f"reachable={reachable}", f"port_open={data.get('port_open')}", f"status={data.get('status')}", f"control_rule={data.get('control_rule')}"],
        "likely_cause": "No issue detected in latest export." if reachable else "Home Assistant port or service may be unreachable.",
        "safe_next_step": "Use backend verified endpoints only for control. Do not call Home Assistant directly from Windows.",
        "confidence": 0.86
    }
