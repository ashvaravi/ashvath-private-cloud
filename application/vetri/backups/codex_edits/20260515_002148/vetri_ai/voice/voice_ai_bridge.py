from __future__ import annotations

from typing import Any

from vetri_ai.main import run_once
from vetri_ai.settings import ROOT_DIR
from vetri_ai.utils.json_utils import load_json


def _feature_enabled() -> bool:
    features = load_json(ROOT_DIR / "config" / "features.json", default={})
    return bool(features.get("voice_ai_integration_v4_enabled", False))


def handle_voice_text(text: str) -> dict[str, Any]:
    if not _feature_enabled():
        return {
            "ok": False,
            "response_text": "",
            "route": "disabled",
            "safety_status": "disabled",
            "should_execute": False,
            "error": "voice_ai_integration_v4_enabled=false",
        }
    try:
        result = run_once(text)
        safety = result.get("safety", {}) if isinstance(result, dict) else {}
        intent = result.get("intent", {}) if isinstance(result, dict) else {}
        return {
            "ok": bool(result.get("ok", False)),
            "response_text": str(result.get("answer", "The AI brain handled the request.")),
            "route": str(intent.get("intent", "vetri_ai")),
            "safety_status": str(safety.get("reason", "evaluated")),
            "should_execute": False,
            "error": None,
        }
    except Exception as error:
        return {
            "ok": False,
            "response_text": "The AI brain had an issue, but the voice system is still running.",
            "route": "voice_ai_bridge_error",
            "safety_status": "safe_fallback",
            "should_execute": False,
            "error": type(error).__name__,
        }
