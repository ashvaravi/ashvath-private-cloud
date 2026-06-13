from __future__ import annotations

import os
import queue
import threading
from typing import Any

from vetri_ai.ai.context_packet import build_context_packet
from vetri_ai.safety.sanitizer import sanitize_value
from vetri_ai.settings import ROOT_DIR, load_env_file
from vetri_ai.utils.json_utils import append_jsonl, load_json
from vetri_ai.utils.time_utils import now_iso


DEFAULT_OPENAI_TIMEOUT_SECONDS = 10.0


def _features() -> dict[str, Any]:
    loaded = load_json(ROOT_DIR / "config" / "features.json", default={})
    return loaded if isinstance(loaded, dict) else {}


def openai_timeout_seconds() -> float:
    value = _features().get("openai_timeout_seconds", DEFAULT_OPENAI_TIMEOUT_SECONDS)
    try:
        timeout = float(value)
    except (TypeError, ValueError):
        timeout = DEFAULT_OPENAI_TIMEOUT_SECONDS
    return max(1.0, min(timeout, 12.0))


def openai_reasoning_enabled() -> bool:
    if os.getenv("VETRI_OPENAI_FORCE_LOCAL", "").strip().lower() in {"1", "true", "yes"}:
        return False
    features = _features()
    if not features.get("openai_reasoning_v4_enabled", False):
        return False
    env = load_env_file()
    return bool(env.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"))


def _build_packet(request: str, relevant_memory: list[dict[str, Any]] | None) -> dict[str, Any]:
    packet = build_context_packet(
        current_request=request,
        relevant_memory=relevant_memory or [],
        allowed_actions=[],
    )
    return sanitize_value(packet)


def _call_openai(packet: dict[str, Any], request: str, timeout_seconds: float) -> dict[str, Any]:
    from openai import OpenAI

    env = load_env_file()
    client = OpenAI(
        api_key=env.get("OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY"),
        timeout=timeout_seconds,
        max_retries=0,
    )
    response = client.responses.create(
        model=env.get("OPENAI_MODEL", "gpt-4o-mini"),
        input=[
            {
                "role": "system",
                "content": (
                    "You are Vetri, a warm but safety-bound private cloud AI companion. "
                    "Do not claim authority to execute actions."
                ),
            },
            {"role": "user", "content": str(packet)},
        ],
        max_output_tokens=450,
    )
    text = getattr(response, "output_text", "").strip()
    append_jsonl(
        ROOT_DIR / "logs" / "ai_requests.jsonl",
        {
            "timestamp": now_iso(),
            "provider": "openai",
            "mode": "openai_reasoning",
            "used_openai": True,
            "request_preview": request[:160],
            "sanitized_context_items": len(packet.get("relevant_memory", [])) if isinstance(packet, dict) else 0,
        },
    )
    return {"ok": True, "used_openai": True, "response": text or local_reasoning_fallback(request)}


def _call_openai_with_outer_timeout(packet: dict[str, Any], request: str, timeout_seconds: float) -> dict[str, Any]:
    result_queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1)

    def worker() -> None:
        try:
            result_queue.put(_call_openai(packet, request, timeout_seconds), block=False)
        except Exception as error:
            result_queue.put(
                {
                    "ok": False,
                    "used_openai": False,
                    "error_type": type(error).__name__,
                    "response": local_reasoning_fallback(request),
                },
                block=False,
            )

    thread = threading.Thread(target=worker, name="vetri-openai-reasoning", daemon=True)
    thread.start()
    try:
        return result_queue.get(timeout=timeout_seconds)
    except queue.Empty:
        return {
            "ok": False,
            "used_openai": False,
            "error_type": "OpenAITimeout",
            "response": local_reasoning_fallback(request),
        }


def reason_with_openai_or_fallback(
    request: str,
    relevant_memory: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    packet = _build_packet(request, relevant_memory)
    if not openai_reasoning_enabled():
        return {"ok": False, "used_openai": False, "response": local_reasoning_fallback(request)}
    timeout_seconds = openai_timeout_seconds()
    try:
        result = _call_openai_with_outer_timeout(packet, request, timeout_seconds)
        if not result.get("response"):
            result["response"] = local_reasoning_fallback(request)
        return result
    except Exception as error:
        return {
            "ok": False,
            "used_openai": False,
            "error_type": type(error).__name__,
            "response": local_reasoning_fallback(request),
        }


def local_reasoning_fallback(request: str, relevant_memory: list[dict[str, Any]] | None = None) -> str:
    lowered = request.lower()
    memory_bits = []
    for item in relevant_memory or []:
        if isinstance(item, dict):
            text = item.get("text") or item.get("summary")
            if text:
                memory_bits.append(str(text))
    latest_export = load_json(ROOT_DIR / "data" / "raw_imports" / "mac_exports" / "export_manifest.json", default={})
    export_note = "Mac export manifest is present" if latest_export else "a fresh Mac export sync may be needed"
    memory_note = "; ".join(memory_bits[-3:]) if memory_bits else "local memory is available when you explicitly save useful context"
    if "architecture" in lowered:
        return (
            "OpenAI reasoning is unavailable right now, so I am using local Vetri memory. "
            "Your Vetri architecture is strong because Windows thinks and remembers, Mac executes approved backend actions, "
            "OpenAI only explains sanitized context, and local policy remains authority."
        )
    if "next safe step" in lowered or "plan" in lowered:
        return (
            "OpenAI reasoning is unavailable right now, so I am using local Vetri memory. "
            "The next safe step is to keep the stable voice layer unchanged, use Mac exports as truth, run read-only monitoring, "
            "and improve one capability at a time with rollback backups."
        )
    return (
        "OpenAI reasoning is unavailable right now, so I am using local Vetri memory. "
        "Your private cloud project is in a strong stage: Mac V4 exports are locked, Windows V4 is being validated, "
        f"and the next focus is keeping voice, memory, diagnosis, and safety stable. Latest local status: {export_note}. "
        f"I remember: {memory_note}."
    )
