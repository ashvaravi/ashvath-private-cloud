from __future__ import annotations

from vetri_ai.skills.mac_export_summary import _load_export


def run() -> dict[str, object]:
    summary = _load_export("latest_dashboard_summary.json")
    if not summary:
        return {"status": "missing_data", "evidence": ["latest_dashboard_summary.json missing"], "likely_cause": "Mac exports are not synced.", "safe_next_step": "Run scripts\\sync_from_mac.ps1.", "confidence": 0.4}
    storage = summary.get("data", {}).get("storage_mount", {})
    mounted = storage.get("mounted")
    return {
        "status": "healthy" if mounted else "needs_attention",
        "evidence": [f"path={storage.get('path')}", f"mounted={mounted}", f"df={storage.get('df')}"],
        "likely_cause": "No issue detected in latest storage metadata." if mounted else "Storage mount may be unavailable.",
        "safe_next_step": "Check the Mac storage mount physically or via backend status; do not alter mount paths automatically.",
        "confidence": 0.83
    }
