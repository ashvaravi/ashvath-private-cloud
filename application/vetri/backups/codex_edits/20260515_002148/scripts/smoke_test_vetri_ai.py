from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ["VETRI_OPENAI_FORCE_LOCAL"] = "1"

from vetri_ai.ai.context_packet import build_context_packet
from vetri_ai.ai.openai_reasoner import reason_with_openai_or_fallback
from vetri_ai.companion.companion_chat import companion_response
from vetri_ai.iot.registry import load_registry
from vetri_ai.memory.memory_store import MemoryStore
from vetri_ai.monitoring.runner import run_monitoring
from vetri_ai.rag.rag_engine import RAGEngine
from vetri_ai.routing.intent_router import IntentRouter
from vetri_ai.safety.policy_engine import PolicyEngine
from vetri_ai.safety.safety_router import SafetyRouter
from vetri_ai.skills.diagnosis_router import diagnose_request
from vetri_ai.skills.diagnosis_skills import summarize_latest_mac_export
from vetri_ai.skills.spotify_nlp import build_search_plan
from vetri_ai.utils.json_utils import load_json
from vetri_ai.voice.voice_ai_bridge import handle_voice_text


def check(name: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(name)
    print(f"PASS {name}")


def run_cli(text: str) -> str:
    completed = subprocess.run([sys.executable, "-m", "vetri_ai.cli", "ask", text], cwd=ROOT, capture_output=True, text=True, timeout=30)
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)
    return completed.stdout.strip()


def main() -> None:
    voice_wake = ROOT / "voice" / "terminal_openwakeword.py"
    before_hash = hashlib.sha256(voice_wake.read_bytes()).hexdigest() if voice_wake.exists() else ""

    for rel in ["config/vetri_policy.json", "config/private_cloud_architecture.json", "config/openai_config.json", "config/rag_config.json", "config/features.json"]:
        check(f"{rel} parses", isinstance(load_json(ROOT / rel, {}), dict))

    check("architecture memory exists", (ROOT / "data" / "project_memory" / "private_cloud_architecture.md").exists())
    check("seeded project memory exists", (ROOT / "data" / "project_memory" / "completed_phases.jsonl").read_text(encoding="utf-8").count("\n") >= 10)
    check("feature config loads", load_json(ROOT / "config" / "features.json", {}).get("voice_ai_integration_v4_enabled") is True)

    plan = build_search_plan("play ஆத்தங்கர மரமே by இளையராஜா")
    check("Spotify NLP module works/imports", bool(plan.queries) and "ஆத்தங்கர மரமே" in str(plan.queries))

    diag = diagnose_request("diagnose backups")
    check("Diagnosis router works/imports", "status" in diag and diag.get("confidence") is not None)

    monitoring = run_monitoring()
    check("Monitoring rules can run manually", "findings" in monitoring and (ROOT / "logs" / "monitoring" / "latest_monitoring_report.json").exists())

    registry = load_registry()
    check("IoT registry loads", "devices" in registry and "groups" in registry)

    router = IntentRouter(load_json(ROOT / "config" / "vetri_actions.json", {}))
    check("router architecture", router.classify("what runs on Windows?").intent == "architecture_question")
    check("router unsafe", router.classify("delete all logs").intent == "unsafe")
    check("router monitoring", router.classify("run a read-only monitoring check").intent == "monitoring_check")
    check("router iot registry", router.classify("show my IoT registry").intent == "iot_registry")

    safety = SafetyRouter(PolicyEngine(load_json(ROOT / "config" / "vetri_policy.json", {})))
    unsafe = router.classify("delete all logs")
    check("unsafe request blocked", not safety.evaluate("delete all logs", unsafe).allowed)

    store = MemoryStore(ROOT)
    remembered = store.remember("remember that smoke test V4 memory works", source="smoke")
    check("Memory write path works", bool(remembered.get("ok")))
    check("Memory review path works", "smoke test V4 memory works" in store.summarize_review())
    tombstone = store.tombstone("forget smoke test V4 memory works")
    check("Forget/tombstone path works", bool(tombstone.get("ok")))

    check("RAG keyword retrieval works", len(RAGEngine(ROOT).retrieve("Home Assistant backend")) > 0)

    packet = build_context_packet("test token secret", latest_status_summary={"api_key": "abc", "safe": "ok"})
    check("context packet excludes secrets", "abc" not in str(packet) and "[REDACTED]" in str(packet))

    fallback = reason_with_openai_or_fallback("help me plan the next safe step")
    check("OpenAI fallback path works", "response" in fallback and bool(fallback["response"]))
    check("Companion chat local fallback works", bool(companion_response("talk to me like a friend about my project")))

    bridge_diag = handle_voice_text("diagnose backups")
    bridge_friend = handle_voice_text("talk to me like a friend about my project")
    bridge_delete = handle_voice_text("delete all logs")
    bridge_devices = handle_voice_text("turn off all devices")
    check("Voice AI bridge imports", isinstance(bridge_diag, dict))
    check("handle_voice_text diagnose backups works", "Diagnosis status" in bridge_diag.get("response_text", ""))
    check("handle_voice_text companion works", bool(bridge_friend.get("response_text")))
    check("handle_voice_text delete all logs is blocked", "Blocked by Vetri safety policy" in bridge_delete.get("response_text", ""))
    check("handle_voice_text turn off all devices does not execute blindly", "not executed" in bridge_devices.get("response_text", "").lower() or "confirmation" in bridge_devices.get("response_text", "").lower())

    check("CLI deterministic architecture response", "Windows" in run_cli("what runs on Windows?"))
    check("existing voice wake file exists", voice_wake.exists())
    after_hash = hashlib.sha256(voice_wake.read_bytes()).hexdigest() if voice_wake.exists() else ""
    check("terminal_openwakeword.py stable file still present", bool(after_hash) and before_hash == after_hash)

    check("Home Assistant direct call not allowed", not PolicyEngine(load_json(ROOT / "config" / "vetri_policy.json", {})).is_direct_home_assistant_allowed())
    check("SSH emergency disabled by default", "disabled by default" in (ROOT / "vetri_ai" / "clients" / "ssh_bridge_client.py").read_text(encoding="utf-8"))

    export_result = summarize_latest_mac_export(ROOT)
    check("Mac export missing/readable state handled", export_result["status"] in {"missing_exports", "read"})

    if (ROOT / "data" / "raw_imports" / "mac_exports" / "export_manifest.json").exists():
        home = run_cli("give me detailed Home Assistant status from the latest Mac export")
        backup = run_cli("give me detailed backup status from the latest Mac export")
        network = run_cli("give me detailed network status from the latest Mac export")
        services = run_cli("give me detailed service status from the latest Mac export")
        dashboard = run_cli("give me dashboard and storage status from the latest Mac export")
        check("detailed Home Assistant export includes reachable", "Reachable:" in home and "port 8123" in home.lower())
        check("detailed backup export includes auth_required and latest backup filename", "auth_required=true" in backup and ".tar.gz" in backup)
        check("detailed network export includes known service ports", "Known service ports:" in network and "vetri_backend_8000" in network)
        check("detailed service export includes docker_available", "docker_available:" in services and "smoke-test-vetri-backend.sh is absent" in services)
        check("detailed dashboard export includes storage and frontend status", "/Volumes/AshvathCloud" in dashboard and "Frontend status: 200" in dashboard)

    print("Vetri AI smoke test completed.")


if __name__ == "__main__":
    main()
