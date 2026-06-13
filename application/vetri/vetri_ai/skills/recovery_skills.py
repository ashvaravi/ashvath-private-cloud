from __future__ import annotations


def suggest_recovery(service: str) -> dict[str, object]:
    return {
        "ok": True,
        "service": service,
        "actions_executed": [],
        "safe_next_steps": ["Review export/backend status.", "Confirm before any restart or write action."],
        "blocked": ["automatic_restart", "destructive_commands"]
    }
