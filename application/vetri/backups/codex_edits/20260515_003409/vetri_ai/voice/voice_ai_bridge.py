from __future__ import annotations

from pathlib import Path
from typing import Any

from vetri_ai.settings import ROOT_DIR
from vetri_ai.utils.json_utils import load_json


def _feature_enabled() -> bool:
    features = load_json(ROOT_DIR / "config" / "features.json", default={})
    return bool(features.get("voice_ai_integration_v4_enabled", False))


def _safe_error(error: BaseException) -> str:
    return type(error).__name__


def _casual_response(text: str) -> str | None:
    normalized = " ".join(text.lower().strip().replace("?", "").replace("!", "").split())
    casual = {
        "how are you",
        "hello",
        "hi",
        "hey",
        "are you there",
    }
    if normalized in casual:
        return (
            "I'm here, Ashva. Your Vetri system is running, and I can help with your private cloud, "
            "memory, diagnosis, music, and Home Assistant."
        )
    return None


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
        casual = _casual_response(text)
        if casual:
            return {
                "ok": True,
                "response_text": casual,
                "route": "companion_greeting",
                "safety_status": "safe_local_fallback",
                "should_execute": False,
                "error": None,
            }

        from vetri_ai.main import run_once

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
            "error": _safe_error(error),
        }
