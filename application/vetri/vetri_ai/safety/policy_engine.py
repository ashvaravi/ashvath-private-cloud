from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    requires_confirmation: bool
    risk: str
    reason: str


class PolicyEngine:
    def __init__(self, policy: dict[str, Any]) -> None:
        self.policy = policy
        self.blocked_keywords = [str(item).lower() for item in policy.get("blocked_keywords", [])]
        self.risk_rules = policy.get("risk_rules", {})

    def evaluate(self, user_input: str, risk: str, requires_confirmation: bool = False) -> PolicyDecision:
        text = user_input.lower()
        for keyword in self.blocked_keywords:
            if keyword and keyword in text:
                return PolicyDecision(False, False, "high", f"Blocked by policy keyword: {keyword}")

        decision = str(self.risk_rules.get(risk, "block")).lower()
        if decision == "block":
            return PolicyDecision(False, False, risk, f"Risk level '{risk}' is blocked by policy.")
        if decision == "confirm" or requires_confirmation:
            return PolicyDecision(True, True, risk, "Allowed only after explicit confirmation and approved route.")
        return PolicyDecision(True, False, risk, "Allowed by policy.")

    def is_direct_home_assistant_allowed(self) -> bool:
        return False

    def openai_enabled_by_policy(self) -> bool:
        return bool(self.policy.get("openai_privacy_rules", {}).get("llm_enabled_default", False))
