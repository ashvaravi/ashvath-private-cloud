from __future__ import annotations

from typing import Callable

from vetri_ai.skills import diagnose_backend, diagnose_backups, diagnose_frontend, diagnose_homeassistant, diagnose_immich, diagnose_network, diagnose_storage, diagnose_voice


ROUTES: dict[str, Callable[[], dict[str, object]]] = {
    "immich": diagnose_immich.run,
    "home assistant": diagnose_homeassistant.run,
    "homeassistant": diagnose_homeassistant.run,
    "backups": diagnose_backups.run,
    "backup": diagnose_backups.run,
    "storage": diagnose_storage.run,
    "network": diagnose_network.run,
    "frontend": diagnose_frontend.run,
    "backend": diagnose_backend.run,
    "voice": diagnose_voice.run
}


def diagnose_request(text: str) -> dict[str, object]:
    lowered = text.lower()
    for key, runner in ROUTES.items():
        if key in lowered:
            return runner()
    return {
        "status": "unknown_target",
        "evidence": [],
        "likely_cause": "I could not identify which subsystem to diagnose.",
        "safe_next_step": "Ask for a specific read-only diagnosis, such as diagnose backups, diagnose network, or diagnose Home Assistant.",
        "confidence": 0.3
    }


def format_diagnosis(result: dict[str, object]) -> str:
    evidence = result.get("evidence", [])
    evidence_lines = []
    if isinstance(evidence, list):
        evidence_lines = [f"- {item}" for item in evidence[:6]]
    return (
        f"Diagnosis status: {result.get('status', 'unknown')}\n"
        "Evidence:\n"
        + ("\n".join(evidence_lines) if evidence_lines else "- none available")
        + f"\nLikely cause: {result.get('likely_cause', 'unknown')}\n"
        + f"Safe next step: {result.get('safe_next_step', 'none')}\n"
        + f"Confidence: {result.get('confidence', 'unknown')}"
    )
