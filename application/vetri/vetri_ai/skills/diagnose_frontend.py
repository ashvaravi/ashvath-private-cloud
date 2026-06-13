from __future__ import annotations

from vetri_ai.skills.mac_export_summary import _load_export


def run() -> dict[str, object]:
    summary = _load_export("latest_dashboard_summary.json")
    if not summary:
        return {"status": "missing_data", "evidence": ["latest_dashboard_summary.json missing"], "likely_cause": "Mac exports are not synced.", "safe_next_step": "Run scripts\\sync_from_mac.ps1.", "confidence": 0.4}
    frontend = summary.get("data", {}).get("frontend", {})
    reachable = frontend.get("reachable")
    return {
        "status": "healthy" if reachable else "needs_attention",
        "evidence": [f"reachable={reachable}", f"status={frontend.get('status')}", f"auth_required={frontend.get('auth_required')}"],
        "likely_cause": "No issue detected in latest frontend metadata." if reachable else "Frontend port may be down or unreachable.",
        "safe_next_step": "Use the Mac frontend smoke test manually if needed; do not restart automatically.",
        "confidence": 0.82
    }
