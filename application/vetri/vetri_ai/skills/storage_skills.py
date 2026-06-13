from __future__ import annotations

from vetri_ai.skills.diagnosis_skills import diagnose


def storage_diagnose() -> dict[str, object]:
    return diagnose("storage")
