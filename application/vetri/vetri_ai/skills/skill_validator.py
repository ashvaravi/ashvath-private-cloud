from __future__ import annotations

from typing import Any, Dict, List


class SkillValidator:
    """
    Validates diagnosis skills before they are trusted.

    Phase 2.4 guardrails:
    - Skills must be read-only.
    - Every step must exist in vetri_actions.json.
    - Every step must be read-only.
    - Every step must use an allowed action type.
    - Diagnosis skills must not call other diagnosis skills.
    """

    ALLOWED_STEP_TYPES = {"backend_api", "ssh_check"}

    def __init__(
        self,
        actions: Dict[str, Dict[str, Any]],
        skills: Dict[str, Dict[str, Any]],
    ) -> None:
        self.actions = actions
        self.skills = skills

    def validate_all(self) -> Dict[str, Any]:
        skill_results: List[Dict[str, Any]] = []

        for skill_name, skill_definition in self.skills.items():
            skill_results.append(
                self.validate_skill(skill_name, skill_definition)
            )

        invalid_skills = [
            item for item in skill_results
            if not item.get("ok", False)
        ]

        issues: List[str] = []
        warnings: List[str] = []

        for item in skill_results:
            for issue in item.get("issues", []):
                issues.append(f"{item.get('skill')}: {issue}")

            for warning in item.get("warnings", []):
                warnings.append(f"{item.get('skill')}: {warning}")

        return {
            "ok": len(invalid_skills) == 0,
            "total_skills": len(skill_results),
            "valid_skills": len(skill_results) - len(invalid_skills),
            "invalid_skills": len(invalid_skills),
            "issues": issues,
            "warnings": warnings,
            "skills": skill_results,
        }

    def validate_skill(
        self,
        skill_name: str,
        skill_definition: Dict[str, Any],
    ) -> Dict[str, Any]:
        issues: List[str] = []
        warnings: List[str] = []
        step_results: List[Dict[str, Any]] = []

        if bool(skill_definition.get("write_access", False)):
            issues.append("Skill declares write_access=true. Diagnosis skills must be read-only.")

        if bool(skill_definition.get("requires_confirmation", False)):
            warnings.append("Skill declares requires_confirmation=true. Read-only diagnosis should not usually require confirmation.")

        steps = skill_definition.get("steps", [])

        if not isinstance(steps, list) or not steps:
            issues.append("Skill has no steps or steps is not a list.")
            steps = []

        for step_name in steps:
            if not isinstance(step_name, str):
                issues.append(f"Invalid step name type: {step_name}")
                continue

            step_result = self.validate_step(step_name)
            step_results.append(step_result)

            if not step_result.get("ok", False):
                for issue in step_result.get("issues", []):
                    issues.append(f"Step '{step_name}': {issue}")

            for warning in step_result.get("warnings", []):
                warnings.append(f"Step '{step_name}': {warning}")

        return {
            "ok": len(issues) == 0,
            "skill": skill_name,
            "description": skill_definition.get("description", ""),
            "service_name": skill_definition.get("service_name"),
            "category": skill_definition.get("category"),
            "severity_if_failed": skill_definition.get("severity_if_failed"),
            "step_count": len(steps),
            "issues": issues,
            "warnings": warnings,
            "steps": step_results,
        }

    def validate_step(self, step_name: str) -> Dict[str, Any]:
        issues: List[str] = []
        warnings: List[str] = []

        action = self.actions.get(step_name)

        if action is None:
            return {
                "ok": False,
                "step": step_name,
                "action_type": None,
                "issues": ["Step action is not defined in vetri_actions.json."],
                "warnings": [],
            }

        action_type = str(action.get("type", "unknown"))

        if action_type not in self.ALLOWED_STEP_TYPES:
            issues.append(
                f"Action type '{action_type}' is not allowed inside diagnosis skills."
            )

        if bool(action.get("write_access", False)):
            issues.append("Action has write_access=true.")

        risk = str(action.get("risk", "unknown")).lower()

        if risk != "low":
            issues.append(f"Diagnosis step risk must be low, found '{risk}'.")

        if bool(action.get("requires_confirmation", False)):
            warnings.append("Action requires confirmation. Diagnosis steps should usually be frictionless read-only checks.")

        if action_type == "backend_api":
            endpoint = action.get("endpoint")
            method = str(action.get("method", "GET")).upper()

            if not endpoint:
                issues.append("backend_api action is missing endpoint.")

            if method != "GET":
                issues.append(f"Diagnosis backend_api step must use GET, found '{method}'.")

        return {
            "ok": len(issues) == 0,
            "step": step_name,
            "action_type": action_type,
            "risk": risk,
            "write_access": bool(action.get("write_access", False)),
            "requires_confirmation": bool(action.get("requires_confirmation", False)),
            "issues": issues,
            "warnings": warnings,
        }
