from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from vetri_ai.settings import ROOT_DIR
from vetri_ai.utils.json_utils import load_json


EXPORT_DIR = ROOT_DIR / "data" / "raw_imports" / "mac_exports"


def _load_export(filename: str, root: Path = ROOT_DIR) -> dict[str, Any] | None:
    loaded = load_json(root / "data" / "raw_imports" / "mac_exports" / filename, default=None)
    return loaded if isinstance(loaded, dict) else None


def _bool_text(value: Any) -> str:
    if value is True:
        return "true"
    if value is False:
        return "false"
    if value is None:
        return "unknown"
    return str(value)


def _warnings_errors(summary: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    warnings = summary.get("warnings") or []
    errors = summary.get("errors") or []
    lines.append("Warnings: " + (", ".join(map(str, warnings)) if warnings else "none"))
    lines.append("Errors: " + (", ".join(map(str, errors)) if errors else "none"))
    return lines


def _auth_required_text(endpoint: dict[str, Any] | None) -> str:
    if not isinstance(endpoint, dict):
        return "Backend endpoint: not present in export"
    auth_required = endpoint.get("auth_required")
    reachable = endpoint.get("reachable")
    status = endpoint.get("status")
    if auth_required:
        return f"Backend endpoint: reachable={_bool_text(reachable)}, status={status}, auth_required=true. This is a protected endpoint, not a failure."
    return f"Backend endpoint: reachable={_bool_text(reachable)}, status={status}, auth_required={_bool_text(auth_required)}"


def _known_ports_lines(known_ports: dict[str, Any] | None) -> list[str]:
    if not isinstance(known_ports, dict) or not known_ports:
        return ["Known ports: none exported"]
    lines = ["Known service ports:"]
    for name in sorted(known_ports):
        port = name.rsplit("_", 1)[-1] if "_" in name else "unknown"
        lines.append(f"- {name}: port {port} open={_bool_text(known_ports[name])}")
    return lines


def summarize_homeassistant(root: Path = ROOT_DIR) -> str:
    summary = _load_export("latest_homeassistant_summary.json", root)
    if summary is None:
        return "Home Assistant export is missing. Run scripts\\sync_from_mac.ps1 when the Mac is reachable."
    data = summary.get("data") if isinstance(summary.get("data"), dict) else {}
    lines = [
        "Home Assistant export status:",
        f"- Reachable: {_bool_text(data.get('reachable'))}",
        f"- Port 8123 open: {_bool_text(data.get('port_open'))}",
        f"- HTTP status code: {data.get('status', 'unknown')}",
        f"- Control rule: {data.get('control_rule', 'not exported')}",
        f"- Export summary: {summary.get('summary', 'not provided')}",
    ]
    summary_text = str(summary.get("summary", "")).lower()
    if "no token" in summary_text or "no token or direct control data exported" in summary_text:
        lines.append("- Token/direct control data: not exported.")
    lines.extend(_warnings_errors(summary))
    return "\n".join(lines)


def summarize_backup(root: Path = ROOT_DIR) -> str:
    summary = _load_export("latest_backup_summary.json", root)
    if summary is None:
        return "Backup export is missing. Run scripts\\sync_from_mac.ps1 when the Mac is reachable."
    data = summary.get("data") if isinstance(summary.get("data"), dict) else {}
    files = data.get("recent_backup_files") if isinstance(data.get("recent_backup_files"), list) else []
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in files:
        if isinstance(item, dict):
            grouped[str(item.get("group", "unknown"))].append(item)
    latest = files[0] if files and isinstance(files[0], dict) else {}
    lines = [
        "Backup export status:",
        f"- local_backup_dir_exists: {_bool_text(data.get('local_backup_dir_exists'))}",
        "- " + _auth_required_text(data.get("backend_endpoint") if isinstance(data.get("backend_endpoint"), dict) else None),
        f"- Latest backup: {latest.get('name', 'unknown')} at {latest.get('modified_at', 'unknown')}",
        "Recent backup files by service:",
    ]
    if not grouped:
        lines.append("- none exported")
    for group in sorted(grouped):
        names = [f"{item.get('name', 'unknown')} ({item.get('modified_at', 'unknown')})" for item in grouped[group][:5]]
        lines.append(f"- {group}: " + "; ".join(names))
    lines.extend(_warnings_errors(summary))
    return "\n".join(lines)


def summarize_network(root: Path = ROOT_DIR) -> str:
    summary = _load_export("latest_network_summary.json", root)
    if summary is None:
        return "Network export is missing. Run scripts\\sync_from_mac.ps1 when the Mac is reachable."
    data = summary.get("data") if isinstance(summary.get("data"), dict) else {}
    tailscale_ips = data.get("tailscale_ipv4") if isinstance(data.get("tailscale_ipv4"), list) else []
    lines = [
        "Network export status:",
        "- " + _auth_required_text(data.get("backend_endpoint") if isinstance(data.get("backend_endpoint"), dict) else None),
        f"- Tailscale IPv4 available: {_bool_text(data.get('tailscale_ipv4_available'))}",
        f"- Tailscale IPv4 addresses: {', '.join(map(str, tailscale_ips)) if tailscale_ips else 'none exported'}",
    ]
    lines.extend(_known_ports_lines(data.get("known_ports") if isinstance(data.get("known_ports"), dict) else None))
    lines.extend(_warnings_errors(summary))
    return "\n".join(lines)


def summarize_services(root: Path = ROOT_DIR) -> str:
    summary = _load_export("latest_service_summary.json", root)
    if summary is None:
        return "Service export is missing. Run scripts\\sync_from_mac.ps1 when the Mac is reachable."
    data = summary.get("data") if isinstance(summary.get("data"), dict) else {}
    launch_agents = data.get("launch_agents") if isinstance(data.get("launch_agents"), dict) else {}
    scripts = data.get("scripts") if isinstance(data.get("scripts"), dict) else {}
    lines = [
        "Service export status:",
        f"- docker_available: {_bool_text(data.get('docker_available'))}",
    ]
    lines.extend(_known_ports_lines(data.get("known_ports") if isinstance(data.get("known_ports"), dict) else None))
    lines.append("LaunchAgents:")
    if launch_agents:
        for name in sorted(launch_agents):
            lines.append(f"- {name}: present={_bool_text(launch_agents[name])}")
    else:
        lines.append("- none exported")
    lines.append("Important scripts:")
    if scripts:
        for name in sorted(scripts):
            lines.append(f"- {name}: present={_bool_text(scripts[name])}")
    else:
        lines.append("- none exported")
    if scripts.get("smoke-test-vetri-backend.sh") is False and scripts.get("test-vetri-backend.sh") is True:
        lines.append("- Backend smoke note: smoke-test-vetri-backend.sh is absent, but test-vetri-backend.sh is present.")
    lines.extend(_warnings_errors(summary))
    return "\n".join(lines)


def summarize_dashboard_storage(root: Path = ROOT_DIR) -> str:
    summary = _load_export("latest_dashboard_summary.json", root)
    if summary is None:
        return "Dashboard export is missing. Run scripts\\sync_from_mac.ps1 when the Mac is reachable."
    data = summary.get("data") if isinstance(summary.get("data"), dict) else {}
    frontend = data.get("frontend") if isinstance(data.get("frontend"), dict) else {}
    storage = data.get("storage_mount") if isinstance(data.get("storage_mount"), dict) else {}
    lines = [
        "Dashboard and storage export status:",
        "- " + _auth_required_text(data.get("endpoint") if isinstance(data.get("endpoint"), dict) else None),
        f"- Frontend reachable: {_bool_text(frontend.get('reachable'))}",
        f"- Frontend status: {frontend.get('status', 'unknown')}",
        f"- Frontend auth_required: {_bool_text(frontend.get('auth_required'))}",
        f"- Storage mount path: {storage.get('path', 'unknown')}",
        f"- Storage mounted: {_bool_text(storage.get('mounted'))}",
        f"- df summary: {storage.get('df', 'not exported')}",
    ]
    lines.extend(_warnings_errors(summary))
    return "\n".join(lines)


def summarize_export_for_request(user_request: str, root: Path = ROOT_DIR) -> str:
    lowered = user_request.lower()
    if "home assistant" in lowered or "homeassistant" in lowered:
        return summarize_homeassistant(root)
    if "backup" in lowered:
        return summarize_backup(root)
    if "network" in lowered or "tailscale" in lowered:
        return summarize_network(root)
    if "service" in lowered or "docker" in lowered or "launch" in lowered:
        return summarize_services(root)
    if "dashboard" in lowered or "storage" in lowered or "frontend" in lowered or "mount" in lowered:
        return summarize_dashboard_storage(root)
    parts = [
        summarize_homeassistant(root),
        "",
        summarize_backup(root),
        "",
        summarize_network(root),
        "",
        summarize_services(root),
        "",
        summarize_dashboard_storage(root),
    ]
    return "\n".join(parts)
