from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VOICE_DIR = Path(__file__).resolve().parent
TOKEN_PATH = VOICE_DIR / "spotify_token.json"

API_BASE = "https://api.spotify.com/v1"


def load_environment() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(VOICE_DIR / ".env")


def normalize_text(text: str) -> str:
    text = str(text or "").lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return apply_spotify_stt_corrections(text)


def apply_spotify_stt_corrections(text: str) -> str:
    """
    Fix common STT mistakes seen during Vetri voice testing.
    Example:
    - "resium music" -> "resume music"
    - "resim music" -> "resume music"
    """

    corrections = {
        "resium music": "resume music",
        "resim music": "resume music",
        "receium music": "resume music",
        "receive music": "resume music",
        "presume music": "resume music",
        "resume audio": "resume music",
        "resium audio": "resume music",
        "pause audio": "pause music",
        "pressium audio": "resume music",
        "play audio": "play music",
        "next audio": "next song",
        "skip audio": "next song",
        "previous audio": "previous song",
        "prev song": "previous song",
        "volume of": "volume up",
        "volium up": "volume up",
        "volium down": "volume down",
    }

    if text in corrections:
        return corrections[text]

    # Word-level corrections.
    words = text.split()
    fixed_words = []

    for word in words:
        if word in {"resium", "resim", "receium", "presume"}:
            fixed_words.append("resume")
        elif word in {"volium", "wolume"}:
            fixed_words.append("volume")
        elif word in {"musik", "musics"}:
            fixed_words.append("music")
        else:
            fixed_words.append(word)

    fixed = " ".join(fixed_words)
    fixed = re.sub(r"\s+", " ", fixed).strip()

    return fixed


def parse_json_or_none(raw: str) -> Any:
    """
    Spotify frequently returns empty bodies for successful playback control commands.
    Never crash on empty/non-JSON response bodies.
    """

    raw = str(raw or "").strip()

    if not raw:
        return None

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw


def load_token() -> dict[str, Any]:
    if not TOKEN_PATH.exists():
        raise RuntimeError(
            "Spotify token not found. Run: python .\\voice\\spotify_auth.py"
        )

    with TOKEN_PATH.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_token(token: dict[str, Any]) -> None:
    with TOKEN_PATH.open("w", encoding="utf-8") as f:
        json.dump(token, f, indent=2)


def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()

    if not value:
        raise RuntimeError(f"{name} missing in Z:\\HomeLLM\\.env")

    return value


def build_basic_auth_header(client_id: str, client_secret: str) -> str:
    raw = f"{client_id}:{client_secret}".encode("utf-8")
    encoded = base64.b64encode(raw).decode("utf-8")
    return f"Basic {encoded}"


def refresh_access_token_if_needed(token: dict[str, Any]) -> dict[str, Any]:
    expires_at = float(token.get("expires_at", 0))

    if expires_at and time.time() < expires_at - 60:
        return token

    refresh_token = token.get("refresh_token")

    if not refresh_token:
        raise RuntimeError("Spotify refresh_token missing. Re-run spotify_auth.py")

    client_id = get_required_env("SPOTIFY_CLIENT_ID")
    client_secret = get_required_env("SPOTIFY_CLIENT_SECRET")

    data = urllib.parse.urlencode(
        {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        }
    ).encode("utf-8")

    request = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=data,
        method="POST",
        headers={
            "Authorization": build_basic_auth_header(client_id, client_secret),
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read().decode("utf-8", errors="replace")
        payload = parse_json_or_none(raw)

    if not isinstance(payload, dict):
        raise RuntimeError(f"Spotify token refresh returned unexpected response: {payload}")

    token["access_token"] = payload["access_token"]
    token["token_type"] = payload.get("token_type", token.get("token_type", "Bearer"))
    token["scope"] = payload.get("scope", token.get("scope", ""))
    token["expires_in"] = payload.get("expires_in", 3600)
    token["expires_at"] = time.time() + int(token["expires_in"])

    if payload.get("refresh_token"):
        token["refresh_token"] = payload["refresh_token"]

    save_token(token)

    return token


def ensure_token_metadata(token: dict[str, Any]) -> dict[str, Any]:
    if "expires_at" not in token:
        expires_in = int(token.get("expires_in", 3600))
        token["expires_at"] = time.time() + expires_in
        save_token(token)

    return token


def get_access_token() -> str:
    token = load_token()
    token = ensure_token_metadata(token)
    token = refresh_access_token_if_needed(token)

    access_token = token.get("access_token")

    if not access_token:
        raise RuntimeError("Spotify access_token missing. Re-run spotify_auth.py")

    return str(access_token)


def spotify_request(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    query: dict[str, Any] | None = None,
    retry_on_401: bool = True,
) -> tuple[int, Any]:
    access_token = get_access_token()

    url = f"{API_BASE}{path}"

    if query:
        url += "?" + urllib.parse.urlencode(query)

    data = None
    headers = {
        "Authorization": f"Bearer {access_token}",
    }

    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url,
        data=data,
        method=method.upper(),
        headers=headers,
    )

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return response.status, parse_json_or_none(raw)

    except urllib.error.HTTPError as exc:
        raw_error = exc.read().decode("utf-8", errors="replace")

        if exc.code == 401 and retry_on_401:
            token = load_token()
            token["expires_at"] = 0
            save_token(token)
            return spotify_request(
                method=method,
                path=path,
                body=body,
                query=query,
                retry_on_401=False,
            )

        return exc.code, parse_json_or_none(raw_error)

    except urllib.error.URLError as exc:
        return 599, f"Spotify network error: {exc}"

    except TimeoutError:
        return 598, "Spotify request timed out."


def spotify_error_message(payload: Any) -> str:
    if isinstance(payload, dict):
        error = payload.get("error")

        if isinstance(error, dict):
            message = error.get("message")
            reason = error.get("reason")

            if message and reason:
                return f"{message} ({reason})"

            if message:
                return str(message)

        if error:
            return str(error)

    if payload:
        return str(payload)

    return "Spotify returned no details."


def get_available_devices() -> list[dict[str, Any]]:
    status, payload = spotify_request("GET", "/me/player/devices")

    if status >= 400:
        raise RuntimeError(f"Could not read Spotify devices: {spotify_error_message(payload)}")

    if not isinstance(payload, dict):
        return []

    return list(payload.get("devices", []))


def get_active_device() -> dict[str, Any] | None:
    devices = get_available_devices()

    for device in devices:
        if device.get("is_active"):
            return device

    return devices[0] if devices else None


def get_current_playback() -> dict[str, Any] | None:
    status, payload = spotify_request("GET", "/me/player")

    if status == 204:
        return None

    if status >= 400:
        raise RuntimeError(f"Could not read Spotify playback state: {spotify_error_message(payload)}")

    if not isinstance(payload, dict):
        return None

    return payload


def get_current_track_summary() -> str:
    playback = get_current_playback()

    if not playback:
        return "Spotify is not currently playing anything."

    item = playback.get("item") or {}
    name = item.get("name", "Unknown track")
    artists = ", ".join(artist.get("name", "Unknown artist") for artist in item.get("artists", []))
    is_playing = bool(playback.get("is_playing"))

    if artists:
        track = f"{name} by {artists}"
    else:
        track = name

    if is_playing:
        return f"Currently playing {track}."

    return f"Spotify is paused on {track}."


def transfer_to_first_device_if_needed() -> str | None:
    playback = get_current_playback()

    if playback and playback.get("device"):
        device_id = playback["device"].get("id")

        if device_id:
            return str(device_id)

    device = get_active_device()

    if not device:
        return None

    device_id = str(device.get("id") or "").strip()

    if not device_id:
        return None

    status, payload = spotify_request(
        "PUT",
        "/me/player",
        body={
            "device_ids": [device_id],
            "play": False,
        },
    )

    if status >= 400:
        raise RuntimeError(f"Could not transfer playback to available device: {spotify_error_message(payload)}")

    return device_id


def play() -> str:
    device_id = transfer_to_first_device_if_needed()

    query = {}

    if device_id:
        query["device_id"] = device_id

    status, payload = spotify_request("PUT", "/me/player/play", query=query or None)

    if status in (200, 202, 204):
        return "Spotify playback resumed."

    return f"Could not resume Spotify playback: {spotify_error_message(payload)}"


def pause() -> str:
    status, payload = spotify_request("PUT", "/me/player/pause")

    if status in (200, 202, 204):
        return "Spotify playback paused."

    return f"Could not pause Spotify playback: {spotify_error_message(payload)}"


def next_track() -> str:
    status, payload = spotify_request("POST", "/me/player/next")

    if status in (200, 202, 204):
        return "Skipped to the next Spotify track."

    return f"Could not skip to the next track: {spotify_error_message(payload)}"


def previous_track() -> str:
    status, payload = spotify_request("POST", "/me/player/previous")

    if status in (200, 202, 204):
        return "Returned to the previous Spotify track."

    return f"Could not go to the previous track: {spotify_error_message(payload)}"


def set_volume(volume_percent: int) -> str:
    safe_volume = max(0, min(100, int(volume_percent)))

    status, payload = spotify_request(
        "PUT",
        "/me/player/volume",
        query={"volume_percent": safe_volume},
    )

    if status in (200, 202, 204):
        return f"Spotify volume set to {safe_volume} percent."

    return f"Could not set Spotify volume: {spotify_error_message(payload)}"


def change_volume(delta: int) -> str:
    playback = get_current_playback()

    if not playback or not playback.get("device"):
        return "I could not find an active Spotify device."

    current = int(playback["device"].get("volume_percent", 50))
    target = max(0, min(100, current + int(delta)))

    return set_volume(target)


def search_track(query_text: str) -> dict[str, Any] | None:
    status, payload = spotify_request(
        "GET",
        "/search",
        query={
            "q": query_text,
            "type": "track",
            "limit": 1,
        },
    )

    if status >= 400:
        raise RuntimeError(f"Could not search Spotify: {spotify_error_message(payload)}")

    if not isinstance(payload, dict):
        return None

    tracks = ((payload.get("tracks") or {}).get("items")) or []

    if not tracks:
        return None

    return tracks[0]


def play_search(query_text: str) -> str:
    query_text = query_text.strip()

    if not query_text:
        return play()

    device_id = transfer_to_first_device_if_needed()

    track = search_track(query_text)

    if not track:
        return f"I could not find {query_text} on Spotify."

    uri = track.get("uri")
    name = track.get("name", "that track")
    artists = ", ".join(artist.get("name", "Unknown artist") for artist in track.get("artists", []))

    if not uri:
        return f"I found {name}, but Spotify did not return a playable URI."

    body = {
        "uris": [uri],
    }

    query = {}

    if device_id:
        query["device_id"] = device_id

    status, payload = spotify_request(
        "PUT",
        "/me/player/play",
        body=body,
        query=query or None,
    )

    if status in (200, 202, 204):
        if artists:
            return f"Playing {name} by {artists} on Spotify."
        return f"Playing {name} on Spotify."

    return f"Could not play {query_text} on Spotify: {spotify_error_message(payload)}"


def extract_search_query(normalized: str, original: str) -> str:
    patterns = [
        r"^play\s+(.+?)\s+on\s+spotify$",
        r"^spotify\s+play\s+(.+)$",
        r"^play\s+(.+)$",
    ]

    for pattern in patterns:
        match = re.match(pattern, normalized)

        if match:
            query = match.group(1).strip()

            blocked = {
                "music",
                "song",
                "songs",
                "spotify",
                "some music",
                "audio",
            }

            if query not in blocked:
                return query

    return ""


def route_text_command(text: str) -> tuple[int, str]:
    original = str(text or "").strip()
    normalized = normalize_text(original)

    if not normalized:
        return 1, "No Spotify command provided."

    try:
        if normalized in {
            "spotify status",
            "what song is playing",
            "what is playing",
            "current song",
            "currently playing",
            "what music is playing",
        }:
            return 0, get_current_track_summary()

        if normalized in {
            "pause spotify",
            "spotify pause",
            "pause music",
            "pause song",
            "stop music",
            "stop spotify",
            "pause",
        }:
            return 0, pause()

        if normalized in {
            "resume spotify",
            "spotify resume",
            "play music",
            "resume music",
            "continue music",
            "play spotify",
            "resume",
            "continue",
        }:
            return 0, play()

        if normalized in {
            "next song",
            "next track",
            "skip song",
            "skip track",
            "spotify next",
            "next spotify",
            "next",
            "skip",
        }:
            return 0, next_track()

        if normalized in {
            "previous song",
            "previous track",
            "go back song",
            "spotify previous",
            "previous spotify",
            "previous",
            "go back",
        }:
            return 0, previous_track()

        if "volume up" in normalized or "increase volume" in normalized:
            return 0, change_volume(+10)

        if "volume down" in normalized or "decrease volume" in normalized or "lower volume" in normalized:
            return 0, change_volume(-10)

        volume_match = re.search(r"(?:set spotify volume|spotify volume|set volume)\s+(\d{1,3})", normalized)

        if volume_match:
            return 0, set_volume(int(volume_match.group(1)))

        search_query = extract_search_query(normalized, original)

        if search_query:
            return 0, play_search(search_query)

        return 1, "No safe Spotify command matched."

    except Exception as exc:
        return 1, f"Spotify command failed: {exc}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Vetri Spotify Control V2B.1")
    parser.add_argument("--text", required=True, help="Spotify command text")
    args = parser.parse_args()

    load_environment()

    return_code, summary = route_text_command(args.text)

    print("========================================")
    print(" Vetri Spotify Control")
    print("========================================")
    print(f"Input: {args.text}")
    print(f"Spotify summary: {summary}")
    print("========================================")

    sys.exit(return_code)


if __name__ == "__main__":
    main()
