from __future__ import annotations

from vetri_ai.utils.json_utils import to_pretty_json


class PromptBuilder:
    def build_explanation_prompt(self, packet: dict[str, object]) -> str:
        return "Explain this sanitized Vetri context without suggesting unsafe actions:\n" + to_pretty_json(packet)

    def build_intent_suggestion_prompt(self, packet: dict[str, object]) -> str:
        return "Return JSON with intent, confidence, reason. Do not execute:\n" + to_pretty_json(packet)
