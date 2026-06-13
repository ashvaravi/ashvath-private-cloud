from __future__ import annotations

from typing import Any, Dict, List


def _status_icon(ok: bool) -> str:
    return "[OK]" if ok else "[FAIL]"


def _safe_get(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = data

    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key)

    return current if current is not None else default


def _find_services_object(data: Dict[str, Any]) -> Any:
    candidates = [
        data.get("services"),
        _safe_get(data, "dashboard", "services"),
        _safe_get(data, "summary", "services"),
    ]

    for candidate in candidates:
        if candidate is not None:
            return candidate

    return None


def _format_service_list(services_data: Any) -> List[str]:
    lines: List[str] = []

    if not isinstance(services_data, dict):
        return lines

    service_count = services_data.get("service_count")
    online_count = services_data.get("online_count")
    degraded_count = services_data.get("degraded_count")
    offline_count = services_data.get("offline_count")
    nested_services = services_data.get("services")

    if service_count is not None:
        lines.append(f"- Service count: {service_count}")
    if online_count is not None:
        lines.append(f"- Online: {online_count}")
    if degraded_count is not None:
        lines.append(f"- Degraded: {degraded_count}")
    if offline_count is not None:
        lines.append(f"- Offline: {offline_count}")

    if isinstance(nested_services, list):
        lines.append("")
        lines.append("Services:")

        for service in nested_services:
            if not isinstance(service, dict):
                continue

            name = service.get("name") or service.get("service_id") or "unknown"
            status = service.get("status", "unknown")
            reachable = service.get("reachable", "unknown")
            response_ms = service.get("response_ms")
            container_health = service.get("container_health")
            container_running = service.get("container_running")

            response_text = f", {response_ms} ms" if response_ms is not None else ""
            health_text = f", health={container_health}" if container_health is not None else ""
            running_text = f", running={container_running}" if container_running is not None else ""

            lines.append(
                f"- {name}: {status}, reachable={reachable}{response_text}{running_text}{health_text}"
            )

    return lines


def _format_backup_locations(data: Dict[str, Any]) -> List[str]:
    lines: List[str] = []
    locations = data.get("locations")

    if not isinstance(locations, list):
        return lines

    lines.append("")
    lines.append("Backup locations:")

    for location in locations:
        if not isinstance(location, dict):
            continue

        name = location.get("name") or location.get("backup_id") or "unknown"
        status = location.get("status", "unknown")
        critical = location.get("critical", "unknown")
        file_count = location.get("file_count", "unknown")
        size_mb = location.get("total_size_mb", "unknown")
        latest_file = location.get("latest_file")
        latest_age = location.get("latest_file_age_hours")
        path = location.get("path")

        lines.append(f"- {name}")
        lines.append(f"  Status: {status}")
        lines.append(f"  Critical: {critical}")
        lines.append(f"  Files: {file_count}")
        lines.append(f"  Size: {size_mb} MB")

        if latest_file is not None:
            lines.append(f"  Latest file: {latest_file}")

        if latest_age is not None:
            lines.append(f"  Latest age: {latest_age} hours")

        if path is not None:
            lines.append(f"  Path: {path}")

    return lines


def _format_network_details(data: Dict[str, Any]) -> List[str]:
    lines: List[str] = []

    hostname = data.get("hostname")
    lan_ips = data.get("lan_ips")
    tailscale = data.get("tailscale")
    internet = data.get("internet")
    backend_port = data.get("backend_port")
    local_services = data.get("local_services")
    notes = data.get("notes")

    if hostname is not None:
        lines.append(f"- Hostname: {hostname}")

    if isinstance(lan_ips, list):
        lines.append("- LAN IPs:")
        if lan_ips:
            for item in lan_ips:
                lines.append(f"  - {item}")
        else:
            lines.append("  - none detected")

    if isinstance(tailscale, dict):
        lines.append("- Tailscale:")
        for key, value in tailscale.items():
            if isinstance(value, (dict, list)):
                lines.append(f"  - {key}: {type(value).__name__}")
            else:
                lines.append(f"  - {key}: {value}")

    if isinstance(internet, dict):
        lines.append("- Internet:")
        for key, value in internet.items():
            if isinstance(value, (dict, list)):
                lines.append(f"  - {key}: {type(value).__name__}")
            else:
                lines.append(f"  - {key}: {value}")

    if isinstance(backend_port, dict):
        lines.append("- Backend port:")
        for key, value in backend_port.items():
            if isinstance(value, (dict, list)):
                lines.append(f"  - {key}: {type(value).__name__}")
            else:
                lines.append(f"  - {key}: {value}")

    if isinstance(local_services, list):
        lines.append("- Local services:")

        for service in local_services:
            if isinstance(service, dict):
                name = service.get("name") or service.get("service") or service.get("id") or "unknown"
                reachable = service.get("reachable", "unknown")
                port = service.get("port")
                status = service.get("status")

                extra_parts = []
                if port is not None:
                    extra_parts.append(f"port={port}")
                if status is not None:
                    extra_parts.append(f"status={status}")

                extra = f", {', '.join(extra_parts)}" if extra_parts else ""
                lines.append(f"  - {name}: reachable={reachable}{extra}")
            else:
                lines.append(f"  - {service}")

    if isinstance(notes, list) and notes:
        lines.append("- Notes:")
        for note in notes:
            lines.append(f"  - {note}")

    return lines


def format_help(result: Dict[str, Any]) -> str:
    return str(result.get("help", "")).strip()


def format_phase_status(result: Dict[str, Any]) -> str:
    phase_status = result.get("phase_status", {})
    enabled = phase_status.get("enabled_capabilities", {})
    architecture = phase_status.get("architecture", {})

    lines = [
        "Vetri AI Phase Status",
        "=====================",
        f"Phase: {phase_status.get('phase', 'unknown')}",
        f"Status: {phase_status.get('status', 'unknown')}",
        "",
        "Architecture:",
        f"- Laptop: {architecture.get('laptop_role', 'unknown')}",
        f"- Mac: {architecture.get('mac_role', 'unknown')}",
        f"- Primary gateway: {architecture.get('primary_gateway', 'unknown')}",
        f"- Fallback gateway: {architecture.get('fallback_gateway', 'unknown')}",
        "",
        "Enabled capabilities:",
    ]

    for name, value in enabled.items():
        lines.append(f"- {_status_icon(bool(value))} {name}: {value}")

    lines.extend(["", f"Next: {phase_status.get('next_phase', 'unknown')}"])
    return "\n".join(lines)


def format_action_list(result: Dict[str, Any]) -> str:
    action_list = result.get("action_list", {})
    actions: List[Dict[str, Any]] = action_list.get("actions", [])

    lines = [
        "Allowlisted Vetri Actions",
        "=========================",
        f"Total actions: {action_list.get('total_actions', len(actions))}",
        "",
    ]

    for action in actions:
        endpoint = action.get("endpoint")
        skill = action.get("skill")
        mode = action.get("mode")

        extra = []
        if endpoint:
            extra.append(f"endpoint: {endpoint}")
        if skill:
            extra.append(f"skill: {skill}")
        if mode:
            extra.append(f"mode: {mode}")

        extra_text = f" | {', '.join(extra)}" if extra else ""

        lines.append(
            f"- {action.get('intent')} "
            f"[{action.get('type')}, risk={action.get('risk')}, write={action.get('write_access')}]"
            f"{extra_text}"
        )
        lines.append(f"  {action.get('description', '')}")

    return "\n".join(lines)


def format_endpoint_validation(result: Dict[str, Any]) -> str:
    validation = result.get("endpoint_validation", {})
    items: List[Dict[str, Any]] = validation.get("results", [])
    all_ok = bool(validation.get("all_reachable", False))

    lines = [
        f"{_status_icon(all_ok)} Backend Endpoint Validation",
        "==============================",
        f"Total: {validation.get('total_backend_endpoints', 0)}",
        f"Reachable: {validation.get('reachable', 0)}",
        f"Failed: {validation.get('failed', 0)}",
        "",
    ]

    for item in items:
        ok = item.get("ok", False)
        status = item.get("status", "unknown")
        code = item.get("status_code")
        code_text = f" ({code})" if code is not None else ""

        lines.append(
            f"{_status_icon(bool(ok))} {item.get('intent')} "
            f"{item.get('method')} {item.get('endpoint')} -> {status}{code_text}"
        )

    return "\n".join(lines)


def format_skill_validation(result: Dict[str, Any]) -> str:
    validation = result.get("skill_validation", {})
    ok = bool(validation.get("ok", False))

    lines = [
        f"{_status_icon(ok)} Diagnosis Skill Validation",
        "================================",
        f"Total skills: {validation.get('total_skills', 0)}",
        f"Valid skills: {validation.get('valid_skills', 0)}",
        f"Invalid skills: {validation.get('invalid_skills', 0)}",
        "",
    ]

    issues = validation.get("issues", [])
    warnings = validation.get("warnings", [])

    if issues:
        lines.append("Issues:")
        for issue in issues:
            lines.append(f"- {issue}")
        lines.append("")

    if warnings:
        lines.append("Warnings:")
        for warning in warnings:
            lines.append(f"- {warning}")
        lines.append("")

    skills = validation.get("skills", [])
    if skills:
        lines.append("Skill details:")
        for skill in skills:
            skill_ok = bool(skill.get("ok", False))
            lines.append(
                f"- {_status_icon(skill_ok)} {skill.get('skill')} "
                f"({skill.get('service_name')}, steps={skill.get('step_count')})"
            )

    if not issues and not warnings:
        lines.append("")
        lines.append("All diagnosis skills passed read-only guardrail validation.")

    return "\n".join(lines)


def format_context_packet(result: Dict[str, Any]) -> str:
    packet = result.get("context_packet", {})
    safe_context = packet.get("safe_context", {})
    allowed_actions = packet.get("allowed_actions", [])

    lines = [
        "[OK] Sanitized Context Packet Preview",
        "=====================================",
        f"Message: {result.get('message')}",
        f"Mode: {packet.get('mode', 'unknown')}",
        f"User request: {packet.get('user_request', 'unknown')}",
        "",
        "Privacy note:",
        f"- {packet.get('privacy_note', '')}",
        "",
        "Execution note:",
        f"- {packet.get('execution_note', '')}",
        "",
        "Allowed actions included in packet:",
    ]

    if allowed_actions:
        for action in allowed_actions:
            lines.append(f"- {action}")
    else:
        lines.append("- none")

    lines.append("")
    lines.append("Safe context top-level keys:")

    if isinstance(safe_context, dict):
        for key in safe_context.keys():
            lines.append(f"- {key}")
    else:
        lines.append(f"- {type(safe_context).__name__}")

    diagnosis = safe_context.get("diagnosis") if isinstance(safe_context, dict) else None

    if isinstance(diagnosis, dict):
        lines.append("")
        lines.append("Diagnosis summary inside packet:")
        lines.append(f"- skill: {diagnosis.get('skill')}")
        lines.append(f"- service: {diagnosis.get('service_name')}")
        lines.append(f"- overall_status: {diagnosis.get('overall_status')}")
        lines.append(f"- steps_run: {diagnosis.get('steps_run')}")
        lines.append(f"- failed_steps: {diagnosis.get('failed_steps')}")

    lines.append("")
    lines.append("Use JSON mode to inspect the full sanitized packet:")
    lines.append("- json preview context immich")

    return "\n".join(lines)


def format_openai_explanation(result: Dict[str, Any]) -> str:
    openai_result = result.get("openai_explanation", {})
    ok = bool(openai_result.get("ok", False))
    parsed = openai_result.get("parsed", {})

    lines = [
        f"{_status_icon(ok)} OpenAI Diagnosis Explanation",
        "=================================",
        f"Message: {result.get('message')}",
        f"OpenAI status: {openai_result.get('status')}",
        f"Model: {openai_result.get('model', 'unknown')}",
        "",
    ]

    if not ok:
        error = openai_result.get("error")
        if error:
            lines.append("Error:")
            lines.append(f"- {error}")
        return "\n".join(lines)

    if isinstance(parsed, dict):
        summary = parsed.get("summary")
        reasoning = parsed.get("reasoning", [])
        safe_next_steps = parsed.get("safe_next_steps", [])
        suggested_intent = parsed.get("suggested_intent")
        requires_action = parsed.get("requires_action")

        if summary:
            lines.append("Summary:")
            lines.append(f"- {summary}")
            lines.append("")

        if isinstance(reasoning, list) and reasoning:
            lines.append("Reasoning:")
            for item in reasoning:
                lines.append(f"- {item}")
            lines.append("")

        if isinstance(safe_next_steps, list) and safe_next_steps:
            lines.append("Safe next steps:")
            for item in safe_next_steps:
                lines.append(f"- {item}")
            lines.append("")

        lines.append("Execution boundary:")
        lines.append("- OpenAI did not execute anything.")
        lines.append("- Local Vetri remains responsible for all validation and execution.")
        lines.append(f"- requires_action: {requires_action}")
        lines.append(f"- suggested_intent: {suggested_intent}")
    else:
        lines.append(str(parsed))

    return "\n".join(lines)


def format_ssh_result(result: Dict[str, Any]) -> str:
    ssh_result = result.get("ssh_result", {})
    ok = bool(ssh_result.get("ok", False))
    stdout = str(ssh_result.get("stdout", "")).strip()
    stderr = str(ssh_result.get("stderr", "")).strip()

    lines = [
        f"{_status_icon(ok)} SSH Connectivity Check",
        "========================",
        f"Intent: {result.get('intent')}",
        f"Confidence: {result.get('confidence')}",
        "",
    ]

    if stdout:
        lines.append("Mac response:")
        lines.append(stdout)

    if stderr:
        lines.append("")
        lines.append("Error:")
        lines.append(stderr)

    return "\n".join(lines)


def format_diagnosis_result(result: Dict[str, Any]) -> str:
    diagnosis = result.get("diagnosis", {})
    ok = bool(result.get("ok", False))
    skill = diagnosis.get("skill", result.get("intent", "unknown"))
    title = skill.replace("_", " ").title()
    interpretation = diagnosis.get("interpretation", {})

    lines = [
        f"{_status_icon(ok)} {title}",
        "=" * (len(title) + 5),
        f"Service: {interpretation.get('service_name', diagnosis.get('service_name', 'unknown'))}",
        f"Category: {interpretation.get('category', diagnosis.get('category', 'unknown'))}",
        f"Severity if failed: {interpretation.get('severity_if_failed', diagnosis.get('severity_if_failed', 'unknown'))}",
        f"Message: {diagnosis.get('message', result.get('message'))}",
        f"Overall status: {diagnosis.get('overall_status', 'unknown')}",
        f"Steps run: {diagnosis.get('steps_run', 0)}",
        f"Failed steps: {diagnosis.get('failed_steps', 0)}",
        "",
    ]

    assessment = interpretation.get("assessment")
    if assessment:
        lines.append("Assessment:")
        lines.append(f"- {assessment}")
        lines.append("")

    expected = interpretation.get("expected_healthy_signals", [])
    if expected:
        lines.append("Expected healthy signals:")
        for item in expected:
            lines.append(f"- {item}")
        lines.append("")

    reasoning = interpretation.get("reasoning", [])
    if reasoning:
        lines.append("Reasoning:")
        for item in reasoning:
            lines.append(f"- {item}")
        lines.append("")

    possible_causes = interpretation.get("possible_causes_if_unhealthy", [])
    if possible_causes:
        lines.append("Possible causes if this becomes unhealthy:")
        for item in possible_causes:
            lines.append(f"- {item}")
        lines.append("")

    issues = interpretation.get("issues", [])
    if issues:
        lines.append("Issues:")
        for item in issues:
            lines.append(f"- {item}")
        lines.append("")

    recommendations = interpretation.get("recommendations", [])
    if recommendations:
        lines.append("Recommended next steps:")
        for item in recommendations:
            lines.append(f"- {item}")
        lines.append("")

    findings = diagnosis.get("findings", [])
    if findings:
        lines.append("Raw findings:")
        for finding in findings:
            lines.append(f"- {finding}")
        lines.append("")

    steps = diagnosis.get("steps", [])
    if steps:
        lines.append("Step details:")
        for step in steps:
            step_ok = bool(step.get("ok", False))
            lines.append(
                f"- {_status_icon(step_ok)} {step.get('step')}: "
                f"{step.get('status')} | {step.get('summary')}"
            )

    return "\n".join(lines)


def format_backend_result(result: Dict[str, Any]) -> str:
    backend_result = result.get("backend_result", {})
    data = backend_result.get("data", {})
    ok = bool(result.get("ok", False))
    intent = result.get("intent", "unknown")
    title = intent.replace("_", " ").title()
    status_code = backend_result.get("status_code")

    lines = [
        f"{_status_icon(ok)} {title}",
        "=" * (len(title) + 5),
        f"Message: {result.get('message')}",
        f"HTTP status: {status_code}",
        f"Confidence: {result.get('confidence')}",
        "",
    ]

    if intent == "dashboard_summary":
        overall = (
            _safe_get(data, "status")
            or _safe_get(data, "overall_status")
            or _safe_get(data, "dashboard", "status")
            or _safe_get(data, "summary", "status")
            or "unknown"
        )

        alerts = (
            _safe_get(data, "alerts")
            or _safe_get(data, "alert_count")
            or _safe_get(data, "dashboard", "alerts")
            or _safe_get(data, "summary", "alerts")
            or 0
        )

        lines.extend(["Cloud summary:", f"- Overall: {overall}", f"- Alerts: {alerts}"])

        service_lines = _format_service_list(_find_services_object(data))
        if service_lines:
            lines.extend(service_lines)

        return "\n".join(lines)

    if intent == "backup_summary":
        health = (
            _safe_get(data, "status")
            or _safe_get(data, "health")
            or _safe_get(data, "overall_status")
            or "unknown"
        )

        lines.extend(["Backup summary:", f"- Status: {health}"])

        for key in ["backup_location_count", "healthy_count", "warning_count", "missing_count"]:
            value = data.get(key)
            if value is not None:
                lines.append(f"- {key}: {value}")

        lines.extend(_format_backup_locations(data))
        return "\n".join(lines)

    if intent == "storage_status":
        lines.append("Storage summary:")

        if isinstance(data, dict):
            preferred_keys = [
                "ssd_path",
                "mounted",
                "private_cloud_path",
                "private_cloud_path_exists",
                "total_gb",
                "used_gb",
                "free_gb",
                "used_percent",
                "status",
            ]

            printed = set()

            for key in preferred_keys:
                if key in data:
                    lines.append(f"- {key}: {data[key]}")
                    printed.add(key)

            for key, value in data.items():
                if key in printed:
                    continue
                if isinstance(value, (dict, list)):
                    lines.append(f"- {key}: {type(value).__name__}")
                else:
                    lines.append(f"- {key}: {value}")

        return "\n".join(lines)

    if intent == "network_status":
        status = data.get("status", "unknown") if isinstance(data, dict) else "unknown"

        lines.extend(["Network summary:", f"- Status: {status}"])

        if isinstance(data, dict):
            lines.extend(_format_network_details(data))

        return "\n".join(lines)

    if isinstance(data, dict):
        lines.append("Returned fields:")

        for key in list(data.keys())[:12]:
            value = data.get(key)
            if isinstance(value, (dict, list)):
                lines.append(f"- {key}: {type(value).__name__}")
            else:
                lines.append(f"- {key}: {value}")
    else:
        lines.append(f"Data: {data}")

    return "\n".join(lines)


def format_blocked_or_unknown(result: Dict[str, Any]) -> str:
    return "\n".join(
        [
            "Vetri did not execute this.",
            "===========================",
            f"Reason: {result.get('message')}",
            f"Intent: {result.get('intent')}",
            f"Confidence: {result.get('confidence')}",
        ]
    )


def format_human_result(result: Dict[str, Any]) -> str:
    if "openai_explanation" in result:
        return format_openai_explanation(result)

    if "context_packet" in result:
        return format_context_packet(result)

    if "skill_validation" in result:
        return format_skill_validation(result)

    if "diagnosis" in result:
        return format_diagnosis_result(result)

    if "help" in result:
        return format_help(result)

    if "phase_status" in result:
        return format_phase_status(result)

    if "action_list" in result:
        return format_action_list(result)

    if "endpoint_validation" in result:
        return format_endpoint_validation(result)

    if "ssh_result" in result:
        return format_ssh_result(result)

    if "backend_result" in result:
        return format_backend_result(result)

    if not result.get("ok", False):
        return format_blocked_or_unknown(result)

    return str(result.get("message", result))
