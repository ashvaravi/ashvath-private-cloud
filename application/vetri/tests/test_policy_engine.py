from vetri_ai.safety.policy_engine import PolicyEngine


def test_direct_ha_forbidden():
    assert PolicyEngine({}).is_direct_home_assistant_allowed() is False
