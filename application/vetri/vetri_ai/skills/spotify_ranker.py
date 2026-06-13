from __future__ import annotations

from difflib import SequenceMatcher
from typing import Any

from vetri_ai.skills.spotify_nlp import normalize_unicode_safe


def similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, normalize_unicode_safe(left), normalize_unicode_safe(right)).ratio()


def score_spotify_result(result: dict[str, Any], title: str, artist: str = "", aliases: list[str] | None = None) -> dict[str, Any]:
    result_title = str(result.get("title") or result.get("name") or "")
    result_artists = " ".join(map(str, result.get("artists", []))) if isinstance(result.get("artists"), list) else str(result.get("artist", ""))
    alias_candidates = aliases or []
    title_score = similarity(title, result_title) if title else 0.0
    artist_score = similarity(artist, result_artists) if artist else 0.0
    alias_score = max([similarity(alias, result_title) for alias in alias_candidates] or [0.0])
    exact_bonus = 0.15 if normalize_unicode_safe(title) == normalize_unicode_safe(result_title) else 0.0
    wrong_title_penalty = 0.35 if artist_score > 0.75 and max(title_score, alias_score) < 0.45 else 0.0
    final = max(0.0, min(1.0, (title_score * 0.58) + (artist_score * 0.18) + (alias_score * 0.16) + exact_bonus - wrong_title_penalty))
    return {
        "title_score": round(title_score, 3),
        "artist_score": round(artist_score, 3),
        "alias_score": round(alias_score, 3),
        "exact_bonus": exact_bonus,
        "wrong_title_penalty": wrong_title_penalty,
        "final_score": round(final, 3),
        "accepted": final >= 0.72 and wrong_title_penalty == 0.0
    }
