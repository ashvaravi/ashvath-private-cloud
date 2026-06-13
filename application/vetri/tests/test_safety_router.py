from vetri_ai.routing.intent_router import IntentRouter
from vetri_ai.safety.policy_engine import PolicyEngine
from vetri_ai.safety.safety_router import SafetyRouter


def test_unsafe_blocked():
    router = IntentRouter()
    policy = PolicyEngine({"risk_rules": {"none": "execute", "low": "execute", "medium": "confirm", "high": "block"}, "blocked_keywords": ["delete all logs"]})
    decision = SafetyRouter(policy).evaluate("delete all logs", router.classify("delete all logs"))
    assert not decision.allowed
