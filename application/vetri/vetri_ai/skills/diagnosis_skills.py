from __future__ import annotations

from pathlib import Path
from typing import Any

from vetri_ai.settings import ROOT_DIR
from vetri_ai.utils.json_utils import load_json, read_jsonl


EXPORT_FILES = [
    "export_manifest.json",
    "latest_status_snapshot.json",
    "latest_dashboard_summary.json",
    "latest_backend_health.json",
    "latest_backup_summary.json",
    "latest_homeassistant_summary.json",
    "latest_network_summary.json",
    "latest_service_summary.json"
]


def export_dir(root: Path = ROOT_DIR) -> Path:
    return root / "data" / "raw_imports" / "mac_exports"


def load_exports(root: Path = ROOT_DIR) -> dict[str, Any]:
    folder = export_dir(root)
    return {name: load_json(folder / name, default=None) for name in EXPORT_FILES}


def summarize_latest_mac_export(root: Path = ROOT_DIR) -> dict[str, Any]:
    folder = export_dir(root)
    manifest_path = folder / "export_manifest.json"
    if not manifest_path.exists():
        return {
            "ok": False,
            "status": "missing_exports",
            "message": "No Mac export manifest found. Run scripts\\sync_from_mac.ps1 when the Mac is reachable.",
            "export_dir": str(folder)
        }
    exports = load_exports(root)
    events = read_jsonl(folder / "sanitized_events.jsonl", limit=10)
    missing = [name for name, value in exports.items() if value is None]
    auth_required = []
    for name, value in exports.items():
        if isinstance(value, dict) and "auth_required" in str(value).lower():
            auth_required.append(name)
    return {
        "ok": True,
        "status": "read",
        "message": "Latest Mac export cache read locally. No SSH or OpenAI call was made.",
        "missing_files": missing,
        "auth_required_files": auth_required,
        "manifest": exports.get("export_manifest.json"),
        "backend_health": exports.get("latest_backend_health.json"),
        "backup_summary": exports.get("latest_backup_summary.json"),
        "network_summary": exports.get("latest_network_summary.json"),
        "service_summary": exports.get("latest_service_summary.json"),
        "homeassistant_summary": exports.get("latest_homeassistant_summary.json"),
        "recent_events_count": len(events)
    }


def diagnose(service: str) -> dict[str, Any]:
    export_summary = summarize_latest_mac_export()
    service_name = service or "private_cloud"
    evidence = []
    if export_summary.get("ok"):
        for key in ["backend_health", "backup_summary", "network_summary", "service_summary", "homeassistant_summary"]:
            value = export_summary.get(key)
            if value is not None:
                evidence.append({key: value})
    else:
        evidence.append({"exports": export_summary.get("message")})
    return {
        "ok": bool(export_summary.get("ok")),
        "service": service_name,
        "status": "read_only_export_based" if export_summary.get("ok") else "missing_export_cache",
        "evidence": evidence[:5],
        "likely_causes": [] if export_summary.get("ok") else ["Mac exports have not been synced to Windows yet."],
        "safe_next_steps": ["Run scripts\\sync_from_mac.ps1 if Mac is reachable.", "Use backend dashboard summary for live status if needed."],
        "requires_confirmation_for_actions": True
    }
