from __future__ import annotations

from typing import Any, Dict, List


class DiagnosisInterpreter:
    """
    Converts raw multi-step diagnosis results into useful local explanations.

    Phase 2.3:
    - Uses skill metadata
    - Still rule-based
    - No OpenAI
    - No RAG
    - No memory writes
    """

    def interpret(self, diagnosis: Dict[str, Any], skill_definition: Dict[str, Any] | None = None) -> Dict[str, Any]:
        skill_definition = skill_definition or {}

        skill = str(diagnosis.get("skill", "unknown"))
        service_name = str(skill_definition.get("service_name", skill.replace("_", " ").title()))
        category = str(skill_definition.get("category", "general"))
        severity_if_failed = str(skill_definition.get("severity_if_failed", "unknown"))
        steps = diagnosis.get("steps", [])

        reasoning: List[str] = []
        issues: List[str] = []
        recommendations: List[str] = []
        healthy_signals_confirmed: List[str] = []

        if not isinstance(steps, list):
            steps = []

        for step in steps:
            if not isinstance(step, dict):
                continue

            step_name = str(step.get("step", "unknown"))
            ok = bool(step.get("ok", False))
            status = str(step.get("status", "unknown"))
            summary = str(step.get("summary", ""))

            if ok:
                reasoning.append(self._healthy_reason(step_name, status, summary))
                healthy_signals_confirmed.append(step_name)
            else:
                issue = self._issue_reason(step_name, status, summary)
                issues.append(issue)

        if not issues:
            assessment = (
                f"{service_name} diagnosis is healthy. "
                "All configured read-only checks passed."
            )
            recommendations.append("No immediate action needed.")
            recommendations.append(f"Use 'json diagnose {self._command_name_from_skill(skill)}' if you want raw backend details.")
        else:
            assessment = (
                f"{service_name} diagnosis needs attention. "
                f"Severity if confirmed: {severity_if_failed}."
            )
            recommendations.extend(self._recommendations_for_issues(skill, issues, skill_definition))

        return {
            "service_name": service_name,
            "category": category,
            "severity_if_failed": severity_if_failed,
            "assessment": assessment,
            "expected_healthy_signals": skill_definition.get("expected_healthy_signals", []),
            "healthy_signals_confirmed": healthy_signals_confirmed,
            "possible_causes_if_unhealthy": skill_definition.get("possible_causes_if_unhealthy", []),
            "safe_next_checks": skill_definition.get("safe_next_checks", []),
            "reasoning": reasoning,
            "issues": issues,
            "recommendations": recommendations,
        }

    def _healthy_reason(self, step_name: str, status: str, summary: str) -> str:
        if step_name == "dashboard_summary":
            return "Dashboard summary is healthy, so the main service layer is responding."

        if step_name == "system_health":
            return "System health check passed, so core Mac project paths and backend basics are intact."

        if step_name == "storage_status":
            return "Storage check passed, so the external SSD/private cloud storage path is available."

        if step_name == "backup_summary":
            return "Backup summary is healthy, so configured backup locations are currently acceptable."

        if step_name == "network_status":
            return "Network status is healthy, so LAN/Tailscale/service reachability checks are acceptable."

        if step_name == "backend_ping":
            return "Backend root endpoint is reachable."

        if step_name == "system_ping":
            return "System ping endpoint is reachable."

        if step_name == "ssh_check":
            return "SSH alias check passed, so the laptop can reach the Mac through vetri-mac."

        return f"{step_name} passed with status '{status}'. {summary}".strip()

    def _issue_reason(self, step_name: str, status: str, summary: str) -> str:
        if step_name == "storage_status":
            return f"Storage check needs attention. Status: {status}. {summary}"

        if step_name == "backup_summary":
            return f"Backup check needs attention. Status: {status}. {summary}"

        if step_name == "network_status":
            return f"Network check needs attention. Status: {status}. {summary}"

        if step_name in {"backend_ping", "system_ping", "system_health"}:
            return f"Backend/system check needs attention. Step: {step_name}. Status: {status}. {summary}"

        if step_name == "ssh_check":
            return f"SSH connectivity check failed or degraded. Status: {status}. {summary}"

        if step_name == "dashboard_summary":
            return f"Dashboard/service summary needs attention. Status: {status}. {summary}"

        return f"{step_name} needs attention. Status: {status}. {summary}"

    def _recommendations_for_issues(
        self,
        skill: str,
        issues: List[str],
        skill_definition: Dict[str, Any],
    ) -> List[str]:
        recommendations: List[str] = []

        safe_next_checks = skill_definition.get("safe_next_checks", [])
        if isinstance(safe_next_checks, list):
            recommendations.extend(str(item) for item in safe_next_checks)

        issue_text = " ".join(issues).lower()

        if "storage" in issue_text or "ssd" in issue_text:
            recommendations.append("Check whether /Volumes/AshvathCloud is mounted on the Mac.")

        if "backup" in issue_text:
            recommendations.append("Inspect latest backup age and backup file count before taking any action.")

        if "network" in issue_text or "tailscale" in issue_text:
            recommendations.append("Verify Tailscale is connected on both laptop and Mac.")

        if "ssh" in issue_text:
            recommendations.append("Manually test: ssh vetri-mac \"hostname; whoami; pwd\"")

        if "backend" in issue_text or "system" in issue_text:
            recommendations.append("Confirm the backend is reachable before considering any recovery step.")

        if not recommendations:
            recommendations.append(f"Use 'json diagnose {self._command_name_from_skill(skill)}' for raw details.")

        # Deduplicate while preserving order
        deduped: List[str] = []
        seen = set()
        for item in recommendations:
            if item not in seen:
                deduped.append(item)
                seen.add(item)

        return deduped

    @staticmethod
    def _command_name_from_skill(skill: str) -> str:
        return skill.replace("_diagnose", "").replace("_", " ")
