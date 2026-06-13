from __future__ import annotations

from typing import Any


class OpenAIClient:
    def __init__(self, enabled: bool = False, api_key: str = "", model: str = "gpt-4o-mini") -> None:
        self.enabled = enabled
        self.api_key = api_key
        self.model = model

    def reason(self, _context_packet: dict[str, Any]) -> dict[str, Any]:
        if not self.enabled:
            return {"ok": False, "status": "disabled", "message": "OpenAI reasoning is disabled by default. Deterministic fallback used."}
        if not self.api_key:
            return {"ok": False, "status": "not_configured", "message": "OpenAI enabled but no API key configured."}
        return {"ok": False, "status": "scaffold_only", "message": "OpenAI API call scaffold present; execution remains local and disabled until configured."}
