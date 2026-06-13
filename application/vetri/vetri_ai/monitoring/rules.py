from __future__ import annotations

from datetime import datetime
from typing import Any

from vetri_ai.monitoring.models import MonitoringFinding
from vetri_ai.skills.mac_export_summary import _load_export


def _parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def evaluate_rules() -> list[MonitoringFinding]:
    findings: list[MonitoringFinding] = []
    manifest = _load_export("export_manifest.json")
    backup = _load_export("latest_backup_summary.json")
    network = _load_export("latest_network_summary.json")
    dashboard = _load_export("latest_dashboard_summary.json")
    home = _load_export("latest_homeassistant_summary.json")
    services = _load_export("latest_service_summary.json")

    findings.append(MonitoringFinding("export_freshness", "ok" if manifest else "warning", "low", "Export manifest is present." if manifest else "Export manifest is missing. Run sync_from_mac.ps1."))

    backup_files = []
    if backup:
        backup_files = backup.get("data", {}).get("recent_backup_files", []) or []
    findings.append(MonitoringFinding("backup_freshness", "ok" if backup_files else "warning", "medium", f"Recent backup files exported: {len(backup_files)}."))

    storage = dashboard.get("data", {}).get("storage_mount", {}) if dashboard else {}
    findings.append(MonitoringFinding("disk_free_space", "ok" if storage.get("mounted") else "warning", "medium", f"Storage mounted={storage.get('mounted')} path={storage.get('path')}."))

    ports = {}
    if network:
        ports.update(network.get("data", {}).get("known_ports", {}) or {})
    closed = [name for name, value in ports.items() if not value]
    findings.append(MonitoringFinding("known_service_ports", "ok" if not closed and ports else "warning", "medium", f"Known ports checked={len(ports)} closed={closed}."))

    frontend = dashboard.get("data", {}).get("frontend", {}) if dashboard else {}
    findings.append(MonitoringFinding("frontend_reachable", "ok" if frontend.get("reachable") else "warning", "medium", f"Frontend reachable={frontend.get('reachable')} status={frontend.get('status')}."))

    home_data = home.get("data", {}) if home else {}
    findings.append(MonitoringFinding("homeassistant_reachable", "ok" if home_data.get("reachable") else "warning", "medium", f"Home Assistant reachable={home_data.get('reachable')} port_open={home_data.get('port_open')}."))

    svc = services.get("data", {}) if services else {}
    findings.append(MonitoringFinding("docker_metadata", "warning" if svc.get("docker_available") is False else "ok", "low", f"docker_available={svc.get('docker_available')}."))
    tailscale = network.get("data", {}).get("tailscale_ipv4_available") if network else None
    findings.append(MonitoringFinding("tailscale_ipv4", "warning" if tailscale is False else "ok", "low", f"tailscale_ipv4_available={tailscale}."))
    agents = svc.get("launch_agents", {}) if isinstance(svc.get("launch_agents"), dict) else {}
    missing_agents = [name for name, present in agents.items() if not present]
    findings.append(MonitoringFinding("launch_agents", "ok" if agents and not missing_agents else "warning", "medium", f"LaunchAgents checked={len(agents)} missing={missing_agents}."))
    return findings
