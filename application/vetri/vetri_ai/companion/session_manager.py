from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CompanionSession:
    mode: str = "companion_chat"
    turns: int = 0
