from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from vetri_ai.ai.context_packet import build_context_packet
from vetri_ai.memory.memory_manager import MemoryManager
from vetri_ai.rag.rag_engine import RAGEngine
from vetri_ai.routing.intent_router import IntentRouter
from vetri_ai.safety.policy_engine import PolicyEngine
from vetri_ai.safety.safety_router import SafetyRouter
from vetri_ai.skills.diagnosis_skills import summarize_latest_mac_export
from vetri_ai.utils.json_utils import load_json


def check(name: str, condition: bool) -> None:
    if not condition:
        raise AssertionError(name)
    print(f"PASS {name}")


def run_cli(text: str) -> str:
    completed = subprocess.run([sys.executable, "-m", "vetri_ai.cli", "ask", text], cwd=ROOT, capture_output=True, text=True, timeout=20)
    if completed.returncode != 0:
        raise AssertionError(completed.stderr)
    return completed.stdout.strip()


def main() -> None:
    voice_wake = ROOT / "voice" / "terminal_openwakeword.py"
    before_hash = hashlib.sha256(voice_wake.read_bytes()).hexdigest() if voice_wake.exists() else ""

    for rel in ["config/vetri_policy.json", "config/private_cloud_architecture.json", "config/openai_config.json", "config/rag_config.json"]:
        check(f"{rel} parses", isinstance(load_json(ROOT / rel, {}), dict))

    check("architecture memory exists", (ROOT / "data" / "project_memory" / "private_cloud_architecture.md").exists())
    check("seeded project memory exists", (ROOT / "data" / "project_memory" / "completed_phases.jsonl").read_text(encoding="utf-8").count("\n") >= 10)

    router = IntentRouter(load_json(ROOT / "config" / "vetri_actions.json", {}))
    check("router architecture", router.classify("what runs on Windows?").intent == "architecture_question")
    check("router unsafe", router.classify("delete all logs").intent == "unsafe")

    safety = SafetyRouter(PolicyEngine(load_json(ROOT / "config" / "vetri_policy.json", {})))
    unsafe = router.classify("delete all logs")
    check("unsafe request blocked", not safety.evaluate("delete all logs", unsafe).allowed)

    memory = MemoryManager(ROOT)
    memory.ensure_memory_files()
    saved = memory.update_user_preference("remember that smoke test writes memory")
    check("memory update works", saved["type"] == "preference")

    check("RAG keyword retrieval works", len(RAGEngine(ROOT).retrieve("Home Assistant backend")) > 0)

    packet = build_context_packet("test token secret", latest_status_summary={"api_key": "abc", "safe": "ok"})
    check("context packet excludes secrets", "abc" not in str(packet) and "[REDACTED]" in str(packet))

    check("CLI deterministic architecture response", "Windows" in run_cli("what runs on Windows?"))
    check("existing voice wake file exists", voice_wake.exists())
    after_hash = hashlib.sha256(voice_wake.read_bytes()).hexdigest() if voice_wake.exists() else ""
    check("terminal_openwakeword.py unchanged during smoke", before_hash == after_hash)

    check("Home Assistant direct call not allowed", not PolicyEngine(load_json(ROOT / "config" / "vetri_policy.json", {})).is_direct_home_assistant_allowed())
    check("OpenAI disabled by default", load_json(ROOT / "config" / "openai_config.json", {}).get("llm_enabled") is False)
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
