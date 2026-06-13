from __future__ import annotations


def confidence_band(score: float) -> str:
    if score >= 0.85:
        return "high"
    if score >= 0.5:
        return "medium"
    return "low"
