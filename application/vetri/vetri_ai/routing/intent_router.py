from __future__ import annotations

import re
from dataclasses import asdict, dataclass
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

    @staticmethod
    def has_tamil(text: str) -> bool:
        return any("\u0b80" <= char <= "\u0bff" for char in text)

    def classify(self, user_input: str) -> IntentResult:
        text = self.normalize(user_input)
        if not text:
            return self._result("unknown", 0.0, "chat", "unknown", "", False, "Empty input")

        unsafe_terms = ["delete all logs", "wipe", "format", "remove docker volume", "expose public port", "firewall", "tailscale acl"]
        if any(term in text for term in unsafe_terms):
            return self._result("unsafe", 0.99, "emergency", "high", "blocked", False, "Blocked destructive or exposure-related request")

        if "do not remember" in text:
            return self._result("memory_no_store", 0.98, "chat", "none", "memory_store", False, "User requested no memory storage")

        if text.startswith("remember that") or text.startswith("remember i prefer") or " remember that " in text or text.startswith("save preference"):
            return self._result("memory_update", 0.96, "chat", "low", "memory_store", False, "Explicit low-risk memory update")

        if text.startswith("forget ") or "forget the preference" in text or "forget last memory" in text:
            return self._result("memory_forget", 0.96, "chat", "low", "memory_store", False, "Explicit memory forget request")

        if "review my personal memory" in text or "what do you remember about how i like to work" in text:
            return self._result("memory_review", 0.94, "chat", "none", "memory_store", False, "Personal memory review")

        if "run a read only monitoring check" in text or "run a read-only monitoring check" in text or "monitoring check" in text:
            return self._result("monitoring_check", 0.95, "diagnostic", "low", "monitoring_runner", False, "Manual read-only monitoring check")

        if "show my iot registry" in text or "iot registry" in text:
            return self._result("iot_registry", 0.95, "chat", "low", "iot_registry", False, "IoT registry query")

        if "what devices are in my bedroom" in text or "what are all the devices in my bedroom" in text or "what are all the devices in my room" in text or ("devices" in text and ("bedroom" in text or "my room" in text)):
            return self._result("iot_room_query", 0.94, "chat", "low", "iot_registry", False, "IoT room device query")

        if "plan" in text and "bedroom" in text and ("light" in text or "device" in text):
            return self._result("iot_plan", 0.94, "chat", "low", "iot_planner", False, "IoT planning request without execution")

        if any(term in text for term in ["turn off", "turn on", "home control", "all devices", "bedroom light", "bedroom fan"]):
            return self._result("home_control", 0.93, "fast", "medium", "backend_home_control", True, "Home Assistant control requires backend route and confirmation")

        if self.has_tamil(user_input) or "spotify" in text or "song was wrong" in text or "tamil" in text or "regional song" in text or "safely search" in text:
            return self._result("spotify_query", 0.9, "chat", "low", "spotify_nlp", False, "Spotify memory or regional NLP query")

        if "mac export" in text or "latest export" in text or "based on the latest export" in text or ("private cloud" in text and ("state" in text or "status" in text)):
            return self._result("mac_export_query", 0.95, "diagnostic", "low", "mac_export_summary", False, "Mac export cache query")

        if text.startswith("diagnose") or "diagnose " in text:
            return self._result("diagnostic", 0.92, "diagnostic", "low", "diagnosis_router", False, "Read-only diagnosis request")

        if "backup" in text and any(word in text for word in ["status", "summary", "healthy", "check"]):
            return self._result("backup_status", 0.9, "fast", "low", "backend_client", False, "Read-only backup status")

        if "storage" in text or "disk" in text:
            return self._result("storage_status", 0.88, "fast", "low", "backend_client", False, "Read-only storage status")

        if "network" in text or "tailscale" in text:
            return self._result("network_status", 0.88, "fast", "low", "backend_client", False, "Read-only network status")

        architecture_terms = ["architecture", "what runs on windows", "what runs on mac", "home assistant control", "windows not directly call home assistant"]
        if any(term in text for term in architecture_terms):
            return self._result("architecture_question", 0.95, "chat", "none", "architecture_memory", False, "Architecture memory query")

        project_terms = ["what phase", "complete today", "completed today", "next safest step", "work on next"]
        if any(term in text for term in project_terms):
            return self._result("project_status", 0.92, "chat", "none", "memory_manager", False, "Project memory query")

        companion_terms = ["how are you", "talk to me", "like a friend", "how am i doing", "project is going", "deeper explanation", "help me plan"]
        if any(term in text for term in companion_terms):
            return self._result("companion_chat", 0.9, "companion_chat", "none", "companion_chat", False, "Companion chat request")

        if "what do you remember" in text or "memory" in text:
            return self._result("memory_query", 0.86, "chat", "none", "rag_engine", False, "Memory query")

        return self._result("companion_chat", 0.72, "companion_chat", "none", "companion_chat", False, "Fallback companion chat; no action execution")

    def _result(self, intent: str, confidence: float, mode: str, risk: str, tool: str, requires_confirmation: bool, reason: str) -> IntentResult:
        action = self.actions.get(intent)
        return IntentResult(intent, confidence, mode, risk, tool, requires_confirmation, reason, action)
