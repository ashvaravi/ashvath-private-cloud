from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


VOICE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = VOICE_DIR.parent
CONFIG_PATH = VOICE_DIR / "ha_config.json"


def load_config() -> dict[str, Any]:
    default = {
        "backend_url": "http://100.79.123.44:8000",
        "entities_endpoint": "/api/v1/home/entities",
        "dashboard_endpoint": "/api/v1/dashboard/summary",
        "api_key_env": "VETRI_API_KEY",
        "backend_url_env": "VETRI_BACKEND_URL",
        "max_entities_to_print": 25,
        "read_only_phrases": [],
        "blocked_action_words": [],
    }

    if not CONFIG_PATH.exists():
        return default

    with CONFIG_PATH.open("r", encoding="utf-8-sig") as f:
        config = json.load(f)

    for key, value in default.items():
        config.setdefault(key, value)

    return config


def load_environment() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(VOICE_DIR / ".env")


def remove_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_text(text: str) -> str:
    text = remove_accents(text)
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def is_blocked_home_action(text: str, config: dict[str, Any]) -> tuple[bool, str | None]:
    normalized = normalize_text(text)

    for word in config.get("blocked_action_words", []):
        if normalize_text(word) in normalized:
            return True, word

    return False, None


def classify_home_read_intent(text: str) -> str:
    normalized = normalize_text(text)

    if any(word in normalized for word in ["unavailable", "offline", "not available", "unknown"]):
        return "unavailable"

    if any(word in normalized for word in ["how many", "count", "number of"]):
        return "count"

    if any(word in normalized for word in ["camera", "cameras", "cctv"]):
        return "domain_camera"

    if any(word in normalized for word in ["switch", "switches"]):
        return "domain_switch"

    if any(word in normalized for word in ["sensor", "sensors"]):
        return "domain_sensor"

    if any(word in normalized for word in ["binary sensor", "binary sensors"]):
        return "domain_binary_sensor"

    if normalized.startswith("find device") or normalized.startswith("search device"):
        return "search"

    if normalized.startswith("find ") or normalized.startswith("search "):
        return "search"

    if any(word in normalized for word in ["working", "healthy", "okay"]) and not any(
        word in normalized for word in ["home assistant", "smart home", "home status"]
    ):
        return "search"

    if any(word in normalized for word in ["list", "show", "devices", "entities"]):
        return "list"

    return "status"


def extract_search_term(text: str) -> str:
    normalized = normalize_text(text)

    remove_phrases = [
        "find device",
        "search device",
        "find",
        "search",
        "is",
        "are",
        "working",
        "healthy",
        "okay",
        "device",
        "devices",
        "home assistant",
        "home",
        "smart",
        "status",
        "show",
        "list",
    ]

    cleaned = normalized

    for phrase in remove_phrases:
        cleaned = re.sub(rf"\b{re.escape(phrase)}\b", " ", cleaned)

    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    return cleaned


def get_backend_url(config: dict[str, Any]) -> str:
    env_name = config.get("backend_url_env", "VETRI_BACKEND_URL")
    backend_url = os.getenv(env_name) or config.get("backend_url", "http://100.79.123.44:8000")
    return backend_url.rstrip("/")


def get_api_key(config: dict[str, Any]) -> str | None:
    env_name = config.get("api_key_env", "VETRI_API_KEY")
    return os.getenv(env_name)


def call_backend_json(config: dict[str, Any], endpoint: str) -> tuple[bool, int | None, Any]:
    backend_url = get_backend_url(config)
    api_key = get_api_key(config)

    url = backend_url + endpoint

    request = urllib.request.Request(url)

    if api_key:
        request.add_header("X-Vetri-API-Key", api_key)

    request.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            status_code = response.status
            raw = response.read().decode("utf-8", errors="replace")

            try:
                return True, status_code, json.loads(raw)
            except json.JSONDecodeError:
                return False, status_code, raw

    except urllib.error.HTTPError as exc:
        try:
            raw_error = exc.read().decode("utf-8", errors="replace")
        except Exception:
            raw_error = str(exc)

        return False, exc.code, raw_error

    except Exception as exc:
        return False, None, str(exc)


def extract_entities(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]

    if not isinstance(payload, dict):
        return []

    if isinstance(payload.get("entities"), list):
        return [item for item in payload["entities"] if isinstance(item, dict)]

    data = payload.get("data")

    if isinstance(data, dict) and isinstance(data.get("entities"), list):
        return [item for item in data["entities"] if isinstance(item, dict)]

    if isinstance(payload.get("items"), list):
        return [item for item in payload["items"] if isinstance(item, dict)]

    return []


def get_entity_id(entity: dict[str, Any]) -> str:
    return str(
        entity.get("entity_id")
        or entity.get("id")
        or entity.get("entity")
        or "unknown_entity"
    )


def get_entity_state(entity: dict[str, Any]) -> str:
    return str(
        entity.get("state")
        or entity.get("status")
        or "unknown"
    )


def get_entity_name(entity: dict[str, Any]) -> str:
    attributes = entity.get("attributes")

    if isinstance(attributes, dict):
        friendly = attributes.get("friendly_name")

        if friendly:
            return str(friendly)

    return str(
        entity.get("name")
        or entity.get("friendly_name")
        or get_entity_id(entity)
    )


def get_entity_domain(entity: dict[str, Any]) -> str:
    entity_id = get_entity_id(entity)

    if "." in entity_id:
        return entity_id.split(".", 1)[0]

    return "unknown"


def summarize_entities(entities: list[dict[str, Any]]) -> dict[str, Any]:
    domains = Counter()
    states = Counter()

    for entity in entities:
        domain = get_entity_domain(entity)
        state = get_entity_state(entity)

        domains[domain] += 1
        states[state] += 1

    unavailable_count = states.get("unavailable", 0) + states.get("unknown", 0)

    return {
        "total": len(entities),
        "domains": domains,
        "states": states,
        "unavailable_count": unavailable_count,
    }


def filter_by_domain(entities: list[dict[str, Any]], domain: str) -> list[dict[str, Any]]:
    return [entity for entity in entities if get_entity_domain(entity) == domain]


def search_entities(entities: list[dict[str, Any]], term: str) -> list[dict[str, Any]]:
    normalized_term = normalize_text(term)

    if not normalized_term:
        return []

    matches = []

    for entity in entities:
        haystack = normalize_text(
            f"{get_entity_name(entity)} {get_entity_id(entity)} {get_entity_state(entity)}"
        )

        if normalized_term in haystack:
            matches.append(entity)

    return matches


def print_entity_table(entities: list[dict[str, Any]], limit: int) -> None:
    if not entities:
        print("No matching Home Assistant entities were returned.")
        return

    print()
    print("Home Assistant entities:")
    print("------------------------")

    for entity in entities[:limit]:
        entity_id = get_entity_id(entity)
        name = get_entity_name(entity)
        state = get_entity_state(entity)
        domain = get_entity_domain(entity)

        print(f"- {name} | {entity_id} | domain={domain} | state={state}")

    if len(entities) > limit:
        print(f"...and {len(entities) - limit} more.")


def get_entities_or_error(config: dict[str, Any]) -> tuple[bool, int, list[dict[str, Any]], str]:
    ok, status_code, payload = call_backend_json(
        config=config,
        endpoint=config.get("entities_endpoint", "/api/v1/home/entities"),
    )

    if not ok:
        if status_code == 401 or status_code == 403:
            return False, 2, [], "Backend rejected the API key. Check VETRI_API_KEY in Z:\\HomeLLM\\.env."

        if isinstance(payload, str) and "not_configured" in payload:
            return False, 2, [], "Home Assistant gateway is reachable, but HOME_ASSISTANT_TOKEN is not configured in the backend."

        return False, 2, [], f"Backend response code: {status_code}. Details: {payload}"

    entities = extract_entities(payload)

    if not entities:
        return False, 1, [], "Home Assistant gateway responded, but no entities were returned."

    return True, 0, entities, "OK"


def build_status_summary(config: dict[str, Any]) -> tuple[str, int]:
    ok, code, entities, error = get_entities_or_error(config)

    if not ok:
        return error, code

    summary = summarize_entities(entities)
    top_domains = ", ".join(
        f"{domain}: {count}"
        for domain, count in summary["domains"].most_common(5)
    )

    unavailable_count = summary["unavailable_count"]

    if unavailable_count == 0:
        return (
            f"Home Assistant is reachable through Vetri backend. "
            f"I found {summary['total']} entities. "
            f"Top domains are {top_domains}. "
            "No unavailable or unknown entities were detected.",
            0,
        )

    return (
        f"Home Assistant is reachable through Vetri backend. "
        f"I found {summary['total']} entities. "
        f"{unavailable_count} entities are unavailable or unknown. "
        f"Top domains are {top_domains}.",
        0,
    )


def handle_domain_query(entities: list[dict[str, Any]], domain: str, max_entities: int) -> int:
    domain_entities = filter_by_domain(entities, domain)
    unavailable = [
        entity for entity in domain_entities
        if get_entity_state(entity) in {"unavailable", "unknown"}
    ]

    print("[HA Voice] SUMMARY")

    if not domain_entities:
        print(f"No Home Assistant entities found for domain: {domain}.")
        return 0

    if unavailable:
        print(
            f"I found {len(domain_entities)} {domain} entities. "
            f"{len(unavailable)} are unavailable or unknown."
        )
    else:
        print(
            f"I found {len(domain_entities)} {domain} entities. "
            "None are unavailable or unknown."
        )

    print_entity_table(domain_entities, limit=max_entities)
    return 0


def handle_search_query(entities: list[dict[str, Any]], text: str, max_entities: int) -> int:
    term = extract_search_term(text)

    # Extra domain shortcuts if the user asks "is camera working?"
    normalized = normalize_text(text)

    if not term and "camera" in normalized:
        term = "camera"

    if not term and "switch" in normalized:
        term = "switch"

    if not term and "sensor" in normalized:
        term = "sensor"

    matches = search_entities(entities, term)

    print("[HA Voice] SUMMARY")

    if not term:
        print("I could not identify which Home Assistant device to search for.")
        return 1

    if not matches:
        print(f"I could not find any Home Assistant entity matching '{term}'.")
        return 0

    unavailable = [
        entity for entity in matches
        if get_entity_state(entity) in {"unavailable", "unknown"}
    ]

    if len(matches) == 1:
        entity = matches[0]
        name = get_entity_name(entity)
        state = get_entity_state(entity)
        entity_id = get_entity_id(entity)

        if state in {"unavailable", "unknown"}:
            print(f"{name} is currently {state}. Entity ID: {entity_id}.")
        else:
            print(f"{name} is available. Current state is {state}. Entity ID: {entity_id}.")

        print_entity_table(matches, limit=max_entities)
        return 0

    if unavailable:
        print(
            f"I found {len(matches)} entities matching '{term}'. "
            f"{len(unavailable)} are unavailable or unknown."
        )
    else:
        print(
            f"I found {len(matches)} entities matching '{term}'. "
            "None are unavailable or unknown."
        )

    print_entity_table(matches, limit=max_entities)
    return 0


def run_home_read_command(text: str, config: dict[str, Any]) -> int:
    blocked, blocked_word = is_blocked_home_action(text, config)

    if blocked:
        print("[HA Voice] BLOCKED")
        print(
            f"Home Assistant action blocked because '{blocked_word}' is a control/write phrase. "
            "V2B supports read-only status and entity intelligence only."
        )
        return 3

    intent = classify_home_read_intent(text)

    ok, code, entities, error = get_entities_or_error(config)

    if not ok:
        print("[HA Voice] ERROR")
        print(error)
        return code

    summary = summarize_entities(entities)
    max_entities = int(config.get("max_entities_to_print", 25))

    if intent == "count":
        print("[HA Voice] SUMMARY")
        print(f"Home Assistant entity count: {summary['total']}")

        if summary["domains"]:
            print("Domain breakdown:")
            for domain, count in summary["domains"].most_common():
                print(f"- {domain}: {count}")

        return 0

    if intent == "unavailable":
        unavailable_entities = [
            entity
            for entity in entities
            if get_entity_state(entity) in {"unavailable", "unknown"}
        ]

        print("[HA Voice] SUMMARY")

        if not unavailable_entities:
            print("No unavailable or unknown Home Assistant entities were detected.")
            return 0

        print(f"Unavailable or unknown entities: {len(unavailable_entities)}")
        print_entity_table(unavailable_entities, limit=max_entities)
        return 0

    if intent == "domain_camera":
        return handle_domain_query(entities, "camera", max_entities)

    if intent == "domain_switch":
        return handle_domain_query(entities, "switch", max_entities)

    if intent == "domain_sensor":
        return handle_domain_query(entities, "sensor", max_entities)

    if intent == "domain_binary_sensor":
        return handle_domain_query(entities, "binary_sensor", max_entities)

    if intent == "search":
        return handle_search_query(entities, text, max_entities)

    if intent == "list":
        print("[HA Voice] SUMMARY")
        print(f"Home Assistant returned {summary['total']} entities.")

        if summary["domains"]:
            print("Top domains:")
            for domain, count in summary["domains"].most_common(8):
                print(f"- {domain}: {count}")

        print_entity_table(entities, limit=max_entities)
        return 0

    spoken, status_code = build_status_summary(config)
    print("[HA Voice] SUMMARY")
    print(spoken)
    return status_code


def main() -> None:
    parser = argparse.ArgumentParser(description="Vetri Home Assistant read-only entity intelligence V2B")
    parser.add_argument(
        "--text",
        type=str,
        required=True,
        help="Home Assistant read-only command text.",
    )

    args = parser.parse_args()

    load_environment()
    config = load_config()

    return_code = run_home_read_command(args.text, config)
    sys.exit(return_code)


if __name__ == "__main__":
    main()
