from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class MonitoringFinding:
    rule: str
    status: str
    severity: str
    message: str

    def to_dict(self) -> dict[str, str]:
        return asdict(self)
