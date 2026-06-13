from vetri_ai.routing.intent_router import IntentRouter


def test_intents():
    router = IntentRouter()
    assert router.classify("what runs on Mac?").intent == "architecture_question"
    assert router.classify("delete all logs").intent == "unsafe"
    assert router.classify("turn off all devices").intent == "home_control"
