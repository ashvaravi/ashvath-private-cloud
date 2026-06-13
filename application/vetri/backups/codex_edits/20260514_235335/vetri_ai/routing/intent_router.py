from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class IntentResult:
    intent: str
    confidence: float
    mode: str
    risk: str
    tool: str
    requires_confirmation: bool
    reason: str
    action: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("action", None)
        return data


class IntentRouter:
    def __init__(self, actions: dict[str, dict[str, Any]] | None = None) -> None:
        self.actions = actions or {}

    @staticmethod
    def normalize(text: str) -> str:
        text = text.strip().lower().replace("_", " ")
        text = re.sub(r"\s+", " ", text)
        return text

    def classify(self, user_input: str) -> IntentResult:
        text = self.normalize(user_input)
        if not text:
            return self._result("unknown", 0.0, "chat", "unknown", "", False, "Empty input")

        unsafe_terms = ["delete all logs", "wipe", "format", "remove docker volume", "expose public port", "firewall", "tailscale acl"]
        if any(term in text for term in unsafe_terms):
            return self._result("unsafe", 0.99, "emergency", "high", "blocked", False, "Blocked destructive or exposure-related request")

        if text.startswith("remember that") or text.startswith("remember i prefer") or text.startswith("save preference"):
            return self._result("memory_update", 0.96, "chat", "low", "memory_manager", False, "Explicit low-risk memory update")

        if "forget last memory" in text:
            return self._result("memory_update", 0.98, "chat", "low", "memory_manager", False, "Explicit memory deletion request")

        if any(term in text for term in ["turn off", "turn on", "home control", "all devices", "bedroom light", "bedroom fan"]):
            return self._result("home_control", 0.93, "fast", "medium", "backend_home_control", True, "Home Assistant control requires backend route and confirmation")

        if "spotify" in text or "song was wrong" in text or "tamil" in text or "regional song" in text:
            return self._result("spotify_query", 0.9, "chat", "low", "spotify_memory_skills", False, "Spotify memory or regional NLP query")

        if "mac export" in text or "latest export" in text or "based on the latest export" in text:
            return self._result("mac_export_query", 0.95, "diagnostic", "low", "diagnosis_skills", False, "Mac export cache query")

        if text.startswith("diagnose") or "diagnose " in text:
            return self._result("diagnostic", 0.92, "diagnostic", "low", "diagnosis_skills", False, "Read-only diagnosis request")

        if "backup" in text and any(word in text for word in ["status", "summary", "healthy", "check"]):
            return self._result("backup_status", 0.9, "fast", "low", "backend_client", False, "Read-only backup status")

        if "storage" in text or "disk" in text:
            return self._result("storage_status", 0.88, "fast", "low", "backend_client", False, "Read-only storage status")

        if "network" in text or "tailscale" in text:
            return self._result("network_status", 0.88, "fast", "low", "backend_client", False, "Read-only network status")

        architecture_terms = ["architecture", "what runs on windows", "what runs on mac", "home assistant control", "windows not directly call home assistant"]
        if any(term in text for term in architecture_terms):
            return self._result("architecture_question", 0.95, "chat", "none", "architecture_memory", False, "Architecture memory query")

        project_terms = ["what phase", "complete today", "completed today", "next safest step", "project status", "work on next"]
        if any(term in text for term in project_terms):
            return self._result("project_status", 0.92, "chat", "none", "memory_manager", False, "Project memory query")

        if "what do you remember" in text or "memory" in text:
            return self._result("memory_query", 0.86, "chat", "none", "rag_engine", False, "Memory query")

        return self._result("chat", 0.7, "chat", "none", "deterministic_chat", False, "Fallback chat; no action execution")

    def _result(self, intent: str, confidence: float, mode: str, risk: str, tool: str, requires_confirmation: bool, reason: str) -> IntentResult:
        action = self.actions.get(intent)
        return IntentResult(intent, confidence, mode, risk, tool, requires_confirmation, reason, action)
