from __future__ import annotations


def strip_cli_prefix(text: str) -> str:
    lowered = text.strip().lower()
    if lowered.startswith("ask "):
        return text.strip()[4:].strip()
    return text.strip()
