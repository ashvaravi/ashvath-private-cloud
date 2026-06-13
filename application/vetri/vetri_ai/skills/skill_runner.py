from __future__ import annotations

from typing import Any

from vetri_ai.skills.diagnosis_skills import diagnose, summarize_latest_mac_export
from vetri_ai.skills.spotify_memory_skills import summarize_spotify_memory


class SkillRunner:
    def __init__(self, *_args: object, **_kwargs: object) -> None:
        pass

    def run_skill(self, skill_name: str, **kwargs: Any) -> dict[str, Any]:
        if skill_name == "mac_export_summary":
            return summarize_latest_mac_export()
        if skill_name == "spotify_memory":
            return summarize_spotify_memory()
        return diagnose(skill_name.replace("_diagnose", ""))
