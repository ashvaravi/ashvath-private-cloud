from __future__ import annotations

from vetri_ai.skills.mac_export_summary import _load_export


def run() -> dict[str, object]:
    summary = _load_export("latest_backend_health.json")
    if not summary:
        return {"status": "missing_data", "evidence": ["latest_backend_health.json missing"], "likely_cause": "Mac exports are not synced.", "safe_next_step": "Run scripts\\sync_from_mac.ps1.", "confidence": 0.4}
    data = summary.get("data", {})
    reachable = data.get("reachable", summary.get("ok"))
    return {
        "status": "healthy" if reachable else "needs_attention",
        "evidence": [f"ok={summary.get('ok')}", f"reachable={reachable}", f"summary={summary.get('summary')}"],
        "likely_cause": "No issue detected in latest backend metadata." if reachable else "Backend may be unreachable or protected endpoint may require auth.",
        "safe_next_step": "Use backend status/export data first; no automatic restart.",
        "confidence": 0.8
    }
