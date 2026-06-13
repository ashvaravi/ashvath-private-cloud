from __future__ import annotations

import argparse
import json
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


VOICE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = VOICE_DIR.parent
CONFIG_PATH = VOICE_DIR / "ha_control_config.json"


def load_config() -> dict[str, Any]:
    default = {
        "backend_url": "http://100.79.123.44:8000",
        "api_key_env": "VETRI_API_KEY",
        "backend_url_env": "VETRI_BACKEND_URL",
        "entities_endpoint": "/api/v1/home/entities",
        "execution_mode": "dry_run",
        "require_confirmation": True,
        "allowed_domains": ["light", "switch", "fan"],
        "allowed_actions": ["turn_on", "turn_off"],
        "entity_allowlist": {},
        "blocked_domains": ["lock", "alarm_control_panel", "cover", "climate", "camera"],
        "blocked_words": [
            "unlock",
            "lock",
            "open",
            "close",
            "delete",
            "remove",
            "restart",
            "reboot",
            "shutdown",
            "set temperature",
            "change temperature",
        ],
        "max_candidates": 10,
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


def get_backend_url(config: dict[str, Any]) -> str:
    env_name = config.get("backend_url_env", "VETRI_BACKEND_URL")
    return (os.getenv(env_name) or config.get("backend_url", "http://100.79.123.44:8000")).rstrip("/")


def get_api_key(config: dict[str, Any]) -> str | None:
    env_name = config.get("api_key_env", "VETRI_API_KEY")
    return os.getenv(env_name)


def call_backend_json(config: dict[str, Any], endpoint: str) -> tuple[bool, int | None, Any]:
    url = get_backend_url(config) + endpoint
    request = urllib.request.Request(url)

    api_key = get_api_key(config)

    if api_key:
        request.add_header("X-Vetri-API-Key", api_key)

    request.add_header("Accept", "application/json")

    try:
        with urllib.request.urlopen(request, timeout=12) as response:
            raw = response.read().decode("utf-8", errors="replace")

            try:
                return True, response.status, json.loads(raw)
            except json.JSONDecodeError:
                return False, response.status, raw

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
    return str(entity.get("entity_id") or entity.get("id") or entity.get("entity") or "unknown_entity")


def get_entity_state(entity: dict[str, Any]) -> str:
    return str(entity.get("state") or entity.get("status") or "unknown")


def get_entity_name(entity: dict[str, Any]) -> str:
    attributes = entity.get("attributes")

    if isinstance(attributes, dict) and attributes.get("friendly_name"):
        return str(attributes["friendly_name"])

    return str(entity.get("name") or entity.get("friendly_name") or get_entity_id(entity))


def get_entity_domain(entity_id: str) -> str:
    if "." not in entity_id:
        return "unknown"

    return entity_id.split(".", 1)[0]


def fetch_entities(config: dict[str, Any]) -> tuple[bool, list[dict[str, Any]], str]:
    ok, status_code, payload = call_backend_json(config, config.get("entities_endpoint", "/api/v1/home/entities"))

    if not ok:
        if status_code in {401, 403}:
            return False, [], "Backend rejected the API key. Check VETRI_API_KEY."

        return False, [], f"Could not fetch Home Assistant entities. Status: {status_code}. Details: {payload}"

    entities = extract_entities(payload)

    if not entities:
        return False, [], "No Home Assistant entities were returned."

    return True, entities, "OK"


def parse_group_target(text: str) -> tuple[str | None, str | None, str]:
    """
    Returns:
      action, group_id, normalized_target

    Supported groups:
      bedroom_lights
      bedroom_all
    """
    action, target = parse_action(text)

    if not action:
        return None, None, target

    normalized = normalize_target_words(target)

    bedroom_lights_phrases = [
        "bedroom lights",
        "room lights",
        "my lights",
        "all bedroom lights",
        "all lights",
    ]

    bedroom_all_phrases = [
        "bedroom",
        "my room",
        "room",
        "bedroom devices",
        "all bedroom devices",
        "all devices",
        "everything in bedroom",
        "everything in my room",
    ]

    for phrase in bedroom_lights_phrases:
        if normalize_target_words(phrase) == normalized or normalize_target_words(phrase) in normalized:
            return action, "bedroom_lights", normalized

    for phrase in bedroom_all_phrases:
        if normalize_target_words(phrase) == normalized or normalize_target_words(phrase) in normalized:
            return action, "bedroom_all", normalized

    return action, None, normalized


def call_backend_group_control(config: dict[str, Any], group_id: str, action: str) -> tuple[bool, int | None, str]:
    backend_url = get_backend_url(config)
    endpoint = str(config.get("group_control_endpoint", "/api/v1/home/control/group/verified"))
    url = backend_url + endpoint

    api_key = get_api_key(config)

    payload = {
        "group_id": group_id,
        "action": action,
        "source": "vetri_voice_v2c_d"
    }

    body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
    )

    request.add_header("Content-Type", "application/json")
    request.add_header("Accept", "application/json")

    if api_key:
        request.add_header("X-Vetri-API-Key", api_key)

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return True, response.status, raw

    except urllib.error.HTTPError as exc:
        try:
            raw_error = exc.read().decode("utf-8", errors="replace")
        except Exception:
            raw_error = str(exc)

        return False, exc.code, raw_error

    except Exception as exc:
        return False, None, str(exc)


def run_group_control_if_matched(text: str, config: dict[str, Any], assume_yes: bool) -> tuple[bool, int]:
    action, group_id, normalized_target = parse_group_target(text)

    if not action or not group_id:
        return False, 0

    group_names = {
        "bedroom_lights": "Bedroom Lights",
        "bedroom_all": "Bedroom Devices",
    }

    friendly_group = group_names.get(group_id, group_id)

    print("[HA Control] GROUP INTENT")
    print(f"Action: {action}")
    print(f"Group ID: {group_id}")
    print(f"Group: {friendly_group}")
    print(f"Target phrase: {normalized_target}")

    if config.get("require_confirmation", True) and not assume_yes:
        answer = input(f"Type YES to confirm {action} for {friendly_group}: ").strip()

        if answer != "YES":
            print("[HA Control] GROUP CONFIRMATION BLOCK")
            print("Confirmation was not provided. No group action was executed.")
            return True, 4

    execution_mode = str(config.get("execution_mode", "backend_live")).lower()

    if execution_mode == "dry_run":
        print("[HA Control] GROUP DRY RUN")
        print(f"Dry run successful. Would execute {action} on {friendly_group}. No device was changed.")
        return True, 0

    if execution_mode != "backend_live":
        print("[HA Control] GROUP POLICY BLOCK")
        print(f"Unsupported execution mode: {execution_mode}.")
        return True, 5

    ok, status_code, response_text = call_backend_group_control(
        config=config,
        group_id=group_id,
        action=action,
    )

    if not ok:
        print("[HA Control] GROUP BACKEND LIVE FAILED SAFELY")
        print(f"Status code: {status_code}")
        print(f"Backend response: {response_text}")
        return True, 6

    print("[HA Control] GROUP BACKEND LIVE REQUEST SENT")
    print(f"Status code: {status_code}")
    print(f"Backend response: {response_text}")

    try:
        parsed_response = json.loads(response_text)

        if isinstance(parsed_response, dict):
            verified = parsed_response.get("verified")
            message = parsed_response.get("message")
            total_entities = parsed_response.get("total_entities")
            verified_count = parsed_response.get("verified_count")
            failed_count = parsed_response.get("failed_count")

            print(f"Verified: {verified}")
            print(f"Verified entities: {verified_count}/{total_entities}")
            print(f"Failed entities: {failed_count}")

            if message:
                print(f"Control summary: {message}")

    except Exception:
        pass

    return True, 0

def parse_action(text: str) -> tuple[str | None, str]:
    normalized = normalize_text(text)

    action_patterns = [
        ("turn_on", ["turn on", "switch on", "start"]),
        ("turn_off", ["turn off", "switch off", "stop"]),
    ]

    for action, phrases in action_patterns:
        for phrase in phrases:
            phrase_norm = normalize_text(phrase)

            if phrase_norm in normalized:
                target = normalized.replace(phrase_norm, " ")
                target = re.sub(r"\s+", " ", target).strip()
                return action, target

    return None, normalized


def contains_blocked_word(text: str, config: dict[str, Any]) -> tuple[bool, str | None]:
    normalized = normalize_text(text)

    for word in config.get("blocked_words", []):
        if normalize_text(word) in normalized:
            return True, word

    return False, None


def normalize_target_words(text: str) -> str:
    normalized = normalize_text(text)

    replacements = {
        " one": " 1",
        " two": " 2",
        " three": " 3",
        " four": " 4",
        " first": " 1",
        " second": " 2",
        "third": "3",
        "bed room": "bedroom"
    }

    padded = f" {normalized} "

    for wrong, right in replacements.items():
        padded = padded.replace(wrong, right)

    return re.sub(r"\s+", " ", padded).strip()


def get_allowlist_aliases(entity_id: str, config: dict[str, Any]) -> list[str]:
    allowlist = config.get("entity_allowlist", {})

    if not isinstance(allowlist, dict):
        return []

    item = allowlist.get(entity_id)

    if not isinstance(item, dict):
        return []

    aliases = item.get("aliases", [])

    if not isinstance(aliases, list):
        aliases = []

    friendly_name = item.get("friendly_name")

    combined = []

    if friendly_name:
        combined.append(str(friendly_name))

    combined.extend(str(alias) for alias in aliases)

    return combined


def search_candidates(entities: list[dict[str, Any]], target: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    normalized_target = normalize_target_words(target)

    allowed_domains = set(config.get("allowed_domains", []))
    candidates = []

    for entity in entities:
        entity_id = get_entity_id(entity)
        domain = get_entity_domain(entity_id)

        if domain not in allowed_domains:
            continue

        alias_text = " ".join(get_allowlist_aliases(entity_id, config))

        haystack = normalize_target_words(
            f"{get_entity_name(entity)} {entity_id} {alias_text}"
        )

        if normalized_target and normalized_target in haystack:
            candidates.append(entity)
            continue

        # Token fallback: useful for "bedroom light one" vs entity_id "ashvas_bedroom_light_1"
        target_tokens = set(normalized_target.split())
        haystack_tokens = set(haystack.split())

        if target_tokens and target_tokens.issubset(haystack_tokens):
            candidates.append(entity)

    return candidates


def entity_is_allowlisted(entity_id: str, config: dict[str, Any]) -> tuple[bool, str | None]:
    allowlist = config.get("entity_allowlist", {})

    if not isinstance(allowlist, dict):
        return False, None

    data = allowlist.get(entity_id)

    if not isinstance(data, dict):
        return False, None

    if not data.get("enabled", False):
        return False, str(data.get("friendly_name") or entity_id)

    return True, str(data.get("friendly_name") or entity_id)


def print_candidates(candidates: list[dict[str, Any]], config: dict[str, Any]) -> None:
    max_candidates = int(config.get("max_candidates", 10))

    if not candidates:
        print("No matching allowed-domain candidates found.")
        return

    print("Matching candidates:")
    for entity in candidates[:max_candidates]:
        entity_id = get_entity_id(entity)
        name = get_entity_name(entity)
        state = get_entity_state(entity)
        domain = get_entity_domain(entity_id)

        allowlisted, alias = entity_is_allowlisted(entity_id, config)
        marker = "ALLOWLISTED" if allowlisted else "not allowlisted"

        print(f"- {name} | {entity_id} | domain={domain} | state={state} | {marker}")

    if len(candidates) > max_candidates:
        print(f"...and {len(candidates) - max_candidates} more.")


def entity_live_enabled(entity_id: str, config: dict[str, Any]) -> tuple[bool, str]:
    """
    V2C-C live policy.

    Allows any entity that is explicitly present in entity_allowlist with:
      enabled: true
      live_enabled: true

    This replaces the old V2C-B1 single live_test_entity_id gate.
    """
    allowlist = config.get("entity_allowlist", {})

    if not isinstance(allowlist, dict):
        return False, "Entity allowlist is invalid."

    item = allowlist.get(entity_id)

    if not isinstance(item, dict):
        return False, f"Entity is not present in allowlist: {entity_id}"

    if not item.get("enabled", False):
        return False, f"Entity is allowlisted but not enabled: {entity_id}"

    if not item.get("live_enabled", False):
        return False, f"Entity is not enabled for live control: {entity_id}"

    return True, "Entity live policy passed."


def call_backend_control(config: dict[str, Any], entity_id: str, action: str) -> tuple[bool, int | None, str]:
    """
    Backend-first live control call.

    Expected backend endpoint:
      POST /api/v1/home/control

    Expected JSON body:
      {
        "entity_id": "...",
        "action": "turn_on" | "turn_off",
        "source": "vetri_voice_v2c_b1"
      }

    If the backend endpoint does not exist yet, this function fails safely.
    It does not call Home Assistant directly.
    """
    backend_url = get_backend_url(config)
    endpoint = str(config.get("control_endpoint", "/api/v1/home/control"))
    url = backend_url + endpoint

    api_key = get_api_key(config)

    payload = {
        "entity_id": entity_id,
        "action": action,
        "source": "vetri_voice_v2c_b1"
    }

    body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        method=str(config.get("control_endpoint_method", "POST")).upper(),
    )

    request.add_header("Content-Type", "application/json")
    request.add_header("Accept", "application/json")

    if api_key:
        request.add_header("X-Vetri-API-Key", api_key)

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return True, response.status, raw

    except urllib.error.HTTPError as exc:
        try:
            raw_error = exc.read().decode("utf-8", errors="replace")
        except Exception:
            raw_error = str(exc)

        return False, exc.code, raw_error

    except Exception as exc:
        return False, None, str(exc)

def run_control_command(text: str, config: dict[str, Any], assume_yes: bool) -> int:
    blocked, blocked_word = contains_blocked_word(text, config)

    if blocked:
        print("[HA Control] BLOCKED")
        print(f"Blocked phrase detected: {blocked_word}. This action is not allowed from voice control.")
        return 3

    group_matched, group_code = run_group_control_if_matched(
        text=text,
        config=config,
        assume_yes=assume_yes,
    )

    if group_matched:
        return group_code

    action, target = parse_action(text)

    if not action:
        print("[HA Control] NO ACTION")
        print("I could not identify a supported Home Assistant control action. Supported actions: turn on, turn off.")
        return 1

    if action not in config.get("allowed_actions", []):
        print("[HA Control] BLOCKED")
        print(f"Action '{action}' is not allowed by ha_control_config.json.")
        return 3

    ok, entities, error = fetch_entities(config)

    if not ok:
        print("[HA Control] ERROR")
        print(error)
        return 2

    candidates = search_candidates(entities, target, config)

    print("[HA Control] INTENT")
    print(f"Action: {action}")
    print(f"Target phrase: {target}")

    if not candidates:
        print("[HA Control] NO MATCH")
        print_candidates(candidates, config)
        return 1

    if len(candidates) > 1:
        print("[HA Control] AMBIGUOUS")
        print("More than one possible entity matched. Refine the name or add a specific allowlist alias.")
        print_candidates(candidates, config)
        return 1

    entity = candidates[0]
    entity_id = get_entity_id(entity)
    domain = get_entity_domain(entity_id)

    if domain in set(config.get("blocked_domains", [])):
        print("[HA Control] BLOCKED")
        print(f"Domain '{domain}' is blocked from voice control.")
        return 3

    allowlisted, friendly_name = entity_is_allowlisted(entity_id, config)

    if not allowlisted:
        print("[HA Control] POLICY BLOCK")
        print(f"Matched entity is not allowlisted: {entity_id}")
        print("Add this entity to voice\\ha_control_config.json -> entity_allowlist before enabling control.")
        print_candidates(candidates, config)
        return 3

    execution_mode = str(config.get("execution_mode", "dry_run")).lower()

    print("[HA Control] POLICY PASSED")
    print(f"Entity: {friendly_name}")
    print(f"Entity ID: {entity_id}")
    print(f"Domain: {domain}")
    print(f"Current state: {get_entity_state(entity)}")
    print(f"Execution mode: {execution_mode}")

    if config.get("require_confirmation", True) and not assume_yes:
        answer = input(f"Type YES to confirm {action} for {friendly_name}: ").strip()

        if answer != "YES":
            print("[HA Control] CONFIRMATION BLOCK")
            print("Confirmation was not provided. No action was executed.")
            return 4

    if execution_mode == "dry_run":
        print("[HA Control] DRY RUN")
        print(f"Dry run successful. Would execute {action} on {entity_id}. No device was changed.")
        return 0

    if execution_mode != "backend_live":
        print("[HA Control] POLICY BLOCK")
        print(f"Unsupported execution mode: {execution_mode}. Use dry_run or backend_live.")
        return 5

    if not config.get("live_enabled", False):
        print("[HA Control] POLICY BLOCK")
        print("Live control is disabled in ha_control_config.json.")
        return 5

    live_allowed, live_message = entity_live_enabled(entity_id, config)

    if not live_allowed:
        print("[HA Control] LIVE POLICY BLOCK")
        print(live_message)
        print("No device was changed.")
        return 5

    print("[HA Control] BACKEND LIVE PREFLIGHT")
    print(f"Backend endpoint: {get_backend_url(config)}{config.get('control_endpoint', '/api/v1/home/control')}")
    print(f"Payload entity_id: {entity_id}")
    print(f"Payload action: {action}")

    ok, status_code, response_text = call_backend_control(
        config=config,
        entity_id=entity_id,
        action=action,
    )

    if not ok:
        print("[HA Control] BACKEND LIVE FAILED SAFELY")
        print(f"Status code: {status_code}")
        print(f"Backend response: {response_text}")
        print("No direct Home Assistant call was attempted from Windows.")
        return 6

    print("[HA Control] BACKEND LIVE REQUEST SENT")
    print(f"Status code: {status_code}")
    print(f"Backend response: {response_text}")

    try:
        parsed_response = json.loads(response_text)

        if isinstance(parsed_response, dict):
            verified = parsed_response.get("verified")
            friendly_name = parsed_response.get("friendly_name")
            after_state = parsed_response.get("after_state")
            message = parsed_response.get("message")

            print(f"Verified: {verified}")
            print(f"Final state: {after_state}")

            if message:
                print(f"Control summary: {message}")
            elif friendly_name and after_state:
                print(f"Control summary: {friendly_name} is now {after_state}.")
    except Exception:
        pass

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Vetri Home Assistant control scaffold V2C-A")
    parser.add_argument("--text", required=True, help="Home Assistant control text.")
    parser.add_argument("--yes", action="store_true", help="Assume confirmation for dry-run tests only.")

    args = parser.parse_args()

    load_environment()
    config = load_config()

    code = run_control_command(args.text, config, assume_yes=args.yes)
    sys.exit(code)


if __name__ == "__main__":
    main()
