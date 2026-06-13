from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass


TAMIL_ALIAS_MAP = {
    "aathangara marame": "ஆத்தங்கர மரமே",
    "athangara marame": "ஆத்தங்கர மரமே",
    "aathangarai marame": "ஆத்தங்கர மரமே",
    "ilayaraja": "இளையராஜா",
    "ilaiyaraaja": "இளையராஜா",
    "ilaiyaraja": "இளையராஜா"
}


@dataclass(frozen=True)
class SpotifySearchPlan:
    title: str
    artist: str
    normalized_title: str
    normalized_artist: str
    queries: list[str]
    notes: list[str]


def normalize_unicode_safe(text: str) -> str:
    text = unicodedata.normalize("NFC", text.strip())
    text = text.casefold()
    text = re.sub(r"[\"'`]+", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_title_artist(text: str) -> tuple[str, str]:
    cleaned = text.strip()
    cleaned = re.sub(r"^(play|search for|find)\s+", "", cleaned, flags=re.I)
    if " by " in cleaned.lower():
        title, artist = re.split(r"\s+by\s+", cleaned, maxsplit=1, flags=re.I)
        return title.strip(), artist.strip()
    return cleaned, ""


def aliases_for(text: str) -> list[str]:
    normalized = normalize_unicode_safe(text)
    aliases = []
    for source, target in TAMIL_ALIAS_MAP.items():
        if source in normalized or target in normalized:
            aliases.extend([source, target])
    return list(dict.fromkeys([item for item in aliases if item and item != text]))


def build_search_plan(text: str) -> SpotifySearchPlan:
    title, artist = split_title_artist(text)
    title_norm = normalize_unicode_safe(title)
    artist_norm = normalize_unicode_safe(artist)
    title_aliases = aliases_for(title)
    artist_aliases = aliases_for(artist)
    queries: list[str] = []
    if title:
        queries.append(title)
        queries.append(f'"{title}"')
    if title and artist:
        queries.append(f"{title} {artist}")
        queries.append(f'"{title}" {artist}')
    for alias in title_aliases:
        queries.append(alias)
        if artist:
            queries.append(f"{alias} {artist}")
    for alias in artist_aliases:
        if title:
            queries.append(f"{title} {alias}")
    queries = list(dict.fromkeys([query.strip() for query in queries if query.strip()]))
    return SpotifySearchPlan(
        title=title,
        artist=artist,
        normalized_title=title_norm,
        normalized_artist=artist_norm,
        queries=queries,
        notes=[
            "Tamil Unicode is preserved.",
            "Title-only and title+artist queries are tried.",
            "Artist match cannot override a weak title match.",
            "Low confidence must not be permanently learned."
        ]
    )


def explain_safe_search(text: str) -> str:
    plan = build_search_plan(text)
    query_lines = "\n".join(f"- {query}" for query in plan.queries)
    return (
        "Safe Spotify regional search plan:\n"
        f"- Parsed title: {plan.title or 'unknown'}\n"
        f"- Parsed artist: {plan.artist or 'not specified'}\n"
        "- Ranking will prefer title confidence first, then artist, aliases, transliteration, and exact/near-match bonuses.\n"
        "- A wrong-title penalty prevents accepting a result only because the artist matches.\n"
        "- If confidence is low, Vetri should ask for clarification and must not permanently learn the mapping.\n"
        "Queries to try:\n"
        f"{query_lines}"
    )
