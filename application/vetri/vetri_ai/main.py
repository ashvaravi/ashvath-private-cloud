from __future__ import annotations

from typing import Any

from vetri_ai.clients.backend_client import BackendClient
from vetri_ai.companion.companion_chat import companion_response
from vetri_ai.iot.planner import plan_iot_action
from vetri_ai.iot.registry import devices_in_room, format_registry
from vetri_ai.logs.audit_logger import AuditLogger
from vetri_ai.memory.memory_manager import MemoryManager
from vetri_ai.memory.memory_store import MemoryStore
from vetri_ai.monitoring.runner import format_monitoring_report, run_monitoring
from vetri_ai.rag.rag_engine import RAGEngine
from vetri_ai.routing.intent_router import IntentRouter
from vetri_ai.safety.policy_engine import PolicyEngine
from vetri_ai.safety.safety_router import SafetyRouter
from vetri_ai.settings import ROOT_DIR, get_settings
from vetri_ai.skills.diagnosis_router import diagnose_request, format_diagnosis
from vetri_ai.skills.mac_export_summary import summarize_export_for_request
from vetri_ai.skills.spotify_memory_skills import explain_regional_song_issue, summarize_spotify_memory
from vetri_ai.skills.spotify_nlp import explain_safe_search
from vetri_ai.utils.json_utils import load_json


def _architecture_answer(text: str) -> str:
    arch = load_json(ROOT_DIR / "config" / "private_cloud_architecture.json", {})
    lowered = text.lower()
    if "what runs on windows" in lowered:
        return "Windows runs the local wake-word voice engine, OpenAI STT only after wake, Spotify control, local TTS, and the Vetri AI brain at `Z:\\HomeLLM`."
    if "what runs on mac" in lowered:
        return "The MacBook runs the private cloud execution layer: Vetri FastAPI backend on port 8000, Immich, Home Assistant, frontend, Uptime Kuma, Tailscale, and the safe export scripts."
    if "home assistant" in lowered:
        return "Home Assistant control is backend-first: Windows never calls Home Assistant directly. Vetri routes approved control to the Mac backend verified endpoints, the token stays on Mac, and the backend verifies final state."
    return "Vetri architecture: Windows is the AI brain and stable voice runtime; Mac is the execution server; FastAPI backend is the control gateway; OpenAI can reason only over sanitized context; local Vetri policy decides execution. Core services: " + ", ".join(arch.get("mac_services", {}).keys())


def _project_answer(text: str, memory: MemoryManager) -> str:
    summary = memory.load_memory_summary()
    lowered = text.lower()
    if "next safest step" in lowered or "work on next" in lowered:
        return "Next safest step: run the Windows smoke test, keep the stable voice route intact, use Mac exports as truth, and expand one safe capability at a time."
    if "today" in lowered:
        latest = summary.get("latest_daily_summary", {})
        return "Today: " + "; ".join(latest.get("milestones", []) + latest.get("decisions", []))
    phases = [item.get("summary", "") for item in summary.get("recent_project_events", [])]
    return "Current phase: Vetri AI Brain V4 integration on top of locked V3A/V3B. Recent checkpoints: " + "; ".join(phases[-8:])


def run_once(user_input: str) -> dict[str, Any]:
    settings = get_settings()
    actions = load_json(settings.config_dir / "vetri_actions.json", {})
    policy = load_json(settings.config_dir / "vetri_policy.json", {})
    router = IntentRouter(actions)
    safety = SafetyRouter(PolicyEngine(policy))
    audit = AuditLogger()
    memory = MemoryManager()
    memory.ensure_memory_files()
    store = MemoryStore()

    intent = router.classify(user_input)
    decision = safety.evaluate(user_input, intent)
    record = {"request": user_input, "intent": intent.to_dict(), "safety": decision.to_dict(), "action_executed": False}

    if not decision.allowed:
        audit.log_command(record | {"result_summary": decision.reason})
        return {"ok": False, "intent": intent.to_dict(), "safety": decision.to_dict(), "answer": "Blocked by Vetri safety policy. " + decision.reason}

    if decision.requires_confirmation:
        audit.log_command(record | {"result_summary": decision.reason})
        return {"ok": False, "intent": intent.to_dict(), "safety": decision.to_dict(), "answer": decision.reason}

    answer: str
    data: Any = None
    if intent.intent == "architecture_question":
        answer = _architecture_answer(user_input)
    elif intent.intent == "project_status":
        answer = _project_answer(user_input, memory)
    elif intent.intent == "memory_no_store":
        answer = "Understood. I will not store that upcoming context as memory."
    elif intent.intent == "memory_review":
        answer = store.summarize_review()
    elif intent.intent == "memory_forget":
        data = store.tombstone(user_input)
        answer = "I added a local tombstone for that forget request. I will avoid using matching memory in future review flows."
    elif intent.intent == "memory_query":
        answer = RAGEngine().answer_from_memory(user_input)
    elif intent.intent == "memory_update":
        data = store.remember(user_input, source="explicit_cli")
        answer = "Saved this safe memory locally." if data.get("ok") else "I did not store that memory: " + str(data.get("reason"))
    elif intent.intent == "mac_export_query":
        answer = summarize_export_for_request(user_input)
    elif intent.intent == "diagnostic":
        data = diagnose_request(user_input)
        answer = format_diagnosis(data)
    elif intent.intent == "monitoring_check":
        data = run_monitoring()
        answer = format_monitoring_report(data)
    elif intent.intent == "iot_registry":
        answer = format_registry()
    elif intent.intent == "iot_room_query":
        answer = devices_in_room("bedroom")
    elif intent.intent == "iot_plan":
        answer = plan_iot_action(user_input)
    elif intent.intent == "spotify_query":
        if "safely search" in user_input.lower() or IntentRouter.has_tamil(user_input):
            answer = explain_safe_search(user_input)
        elif "wrong" in user_input.lower() or "tamil" in user_input.lower() or "regional" in user_input.lower():
            answer = explain_regional_song_issue()
        else:
            data = summarize_spotify_memory()
            answer = "Spotify memory summary: " + str({k: data.get(k) for k in ["status", "learned_tracks_count", "aliases_count", "failed_searches_count", "stt_corrections_count"]})
    elif intent.intent == "companion_chat":
        answer = companion_response(user_input)
    elif intent.intent in {"backup_status", "storage_status", "network_status"}:
        endpoint = {"backup_status": "/api/v1/backups/summary", "storage_status": "/api/v1/storage/status", "network_status": "/api/v1/network/status"}[intent.intent]
        data = BackendClient(settings.backend_url, settings.api_key).safe_get(endpoint)
        answer = f"Backend read-only request result: {data.get('status', 'ok' if data.get('ok') else 'failed')}."
    else:
        answer = "I can answer from local Vetri memory, summarize Mac exports, run read-only diagnosis, run manual monitoring, plan IoT safely, and block unsafe actions."

    audit.log_command(record | {"action_executed": False, "result_summary": answer[:300]})
    return {"ok": True, "intent": intent.to_dict(), "safety": decision.to_dict(), "answer": answer, "data": data}


def main() -> None:
    import sys
    text = " ".join(sys.argv[1:]).strip()
    if not text:
        print("Usage: python -m vetri_ai.cli ask \"question\"")
        return
    result = run_once(text)
    print(result["answer"])


if __name__ == "__main__":
    main()
