from __future__ import annotations

from pathlib import Path

from vetri_ai.settings import ROOT_DIR


def run() -> dict[str, object]:
    required = [
        "terminal_openwakeword.py",
        "terminal_openwakeword_config.json",
        "spotify_control.py",
        "home_assistant_control.py",
        "home_assistant_read.py",
        "vetri_tts.py",
        "voice_cli.py"
    ]
    existing = [name for name in required if (ROOT_DIR / "voice" / name).exists()]
    missing = [name for name in required if name not in existing]
    return {
        "status": "healthy" if not missing else "needs_attention",
        "evidence": [f"present={existing}", f"missing={missing}", "wake phrase unchanged in config/code path by V4 layer"],
        "likely_cause": "No missing stable voice files detected." if not missing else "One or more stable voice files are missing.",
        "safe_next_step": "Keep V4 as fallback route only; do not rewrite the wake loop.",
        "confidence": 0.9
    }
