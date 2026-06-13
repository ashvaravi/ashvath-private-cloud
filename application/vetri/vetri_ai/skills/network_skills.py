from __future__ import annotations

from vetri_ai.skills.diagnosis_skills import diagnose


def network_diagnose() -> dict[str, object]:
    return diagnose("network")
