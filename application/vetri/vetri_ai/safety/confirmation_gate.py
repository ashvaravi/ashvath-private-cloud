from __future__ import annotations


def confirmation_required(risk: str) -> bool:
    return risk == "medium"
