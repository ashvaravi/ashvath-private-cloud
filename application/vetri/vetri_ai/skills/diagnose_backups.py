from __future__ import annotations

from vetri_ai.skills.mac_export_summary import _load_export


def run() -> dict[str, object]:
    summary = _load_export("latest_backup_summary.json")
    if not summary:
        return {"status": "missing_data", "evidence": ["latest_backup_summary.json missing"], "likely_cause": "Mac exports are not synced.", "safe_next_step": "Run scripts\\sync_from_mac.ps1.", "confidence": 0.4}
    data = summary.get("data", {})
    files = data.get("recent_backup_files", []) if isinstance(data.get("recent_backup_files"), list) else []
    latest = files[0] if files else {}
    ok = bool(data.get("local_backup_dir_exists")) and bool(files)
    return {
        "status": "healthy" if ok else "needs_attention",
        "evidence": [f"local_backup_dir_exists={data.get('local_backup_dir_exists')}", f"recent_backup_count={len(files)}", f"latest={latest.get('name')} at {latest.get('modified_at')}", "backend_endpoint auth_required is protected endpoint, not failure"],
        "likely_cause": "No issue detected in latest backup metadata." if ok else "Backup directory or recent backup metadata is missing.",
        "safe_next_step": "Review backup metadata; do not delete or rotate backups automatically.",
        "confidence": 0.84
    }
