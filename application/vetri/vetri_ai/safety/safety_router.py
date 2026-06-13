from __future__ import annotations

from dataclasses import dataclass, asdict

from vetri_ai.routing.intent_router import IntentResult
from vetri_ai.safety.policy_engine import PolicyEngine


@dataclass(frozen=True)
class SafetyDecision:
    allowed: bool
    requires_confirmation: bool
    risk: str
    reason: str
    execute: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class SafetyRouter:
    def __init__(self, policy_engine: PolicyEngine) -> None:
        self.policy_engine = policy_engine

    def evaluate(self, user_input: str, intent_result: IntentResult) -> SafetyDecision:
        if intent_result.intent == "home_control":
            return SafetyDecision(
                allowed=True,
                requires_confirmation=True,
                risk="medium",
                reason="Home Assistant control is not executed by the chat brain. It must route through the Mac backend with confirmation and verification.",
                execute=False,
            )

        decision = self.policy_engine.evaluate(user_input, intent_result.risk, intent_result.requires_confirmation)
        execute = decision.allowed and not decision.requires_confirmation and intent_result.risk in {"none", "low"}
        return SafetyDecision(decision.allowed, decision.requires_confirmation, decision.risk, decision.reason, execute)
