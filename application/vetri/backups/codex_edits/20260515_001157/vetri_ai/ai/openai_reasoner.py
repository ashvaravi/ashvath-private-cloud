from __future__ import annotations

import os
from typing import Any

from vetri_ai.ai.context_packet import build_context_packet
from vetri_ai.safety.sanitizer import sanitize_value
from vetri_ai.settings import load_env_file
from vetri_ai.utils.json_utils import append_jsonl, load_json
from vetri_ai.settings import ROOT_DIR
from vetri_ai.utils.time_utils import now_iso


def openai_reasoning_enabled() -> bool:
    features = load_json(ROOT_DIR / "config" / "features.json", default={})
    if not features.get("openai_reasoning_v4_enabled", False):
        return False
    env = load_env_file()
    return bool(env.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"))


def reason_with_openai_or_fallback(request: str, relevant_memory: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    packet = build_context_packet(
        current_request=request,
        relevant_memory=relevant_memory or [],
        allowed_actions=[]
    )
    packet = sanitize_value(packet)
    if not openai_reasoning_enabled():
        return {"ok": False, "used_openai": False, "response": local_reasoning_fallback(request)}
    try:
        from openai import OpenAI
        env = load_env_file()
        client = OpenAI(api_key=env.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"), timeout=8)
        response = client.responses.create(
            model=env.get("OPENAI_MODEL", "gpt-4o-mini"),
            input=[
                {"role": "system", "content": "You are Vetri, a warm but safety-bound private cloud AI companion. Do not claim authority to execute actions."},
                {"role": "user", "content": str(packet)}
            ],
            max_output_tokens=450
        )
        append_jsonl(
            ROOT_DIR / "logs" / "ai_requests.jsonl",
            {
                "timestamp": now_iso(),
                "provider": "openai",
                "mode": "openai_reasoning",
                "used_openai": True,
                "request_preview": request[:160],
                "sanitized_context_items": len(packet.get("relevant_memory", [])) if isinstance(packet, dict) else 0
            }
        )
        return {"ok": True, "used_openai": True, "response": getattr(response, "output_text", "").strip() or local_reasoning_fallback(request)}
    except Exception:
        return {"ok": False, "used_openai": False, "response": local_reasoning_fallback(request)}


def local_reasoning_fallback(request: str) -> str:
    lowered = request.lower()
    if "architecture" in lowered:
        return "Your Vetri architecture is solid because responsibility is split clearly: Windows thinks and remembers, Mac executes approved backend actions, OpenAI explains only sanitized context, and local policy remains authority."
    if "next safe step" in lowered or "plan" in lowered:
        return "The next safe step is to keep the stable voice layer unchanged, use the Mac exports as truth, run read-only monitoring, then improve one capability at a time with rollback backups."
    return "I can talk this through locally. You are building this in a sensible direction: preserve stable foundations, add memory and diagnosis carefully, and keep execution behind deterministic safety routes."
