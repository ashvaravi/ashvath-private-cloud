from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ControlPlan:
    ok: bool
    target: str
    route: str
    risk: str
    requires_confirmation: bool
    steps: list[str]
    blocked_reason: str = ""
