from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import sounddevice as sd
import soundfile as sf
from dotenv import load_dotenv
from openai import OpenAI


VOICE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = VOICE_DIR / "voice_config.json"
LOG_DIR = VOICE_DIR / "logs"
SESSION_LOG_PATH = LOG_DIR / "voice_sessions.jsonl"
STATE_PATH = VOICE_DIR / "voice_state.json"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing config file: {CONFIG_PATH}")

    with CONFIG_PATH.open("r", encoding="utf-8-sig") as f:
        return json.load(f)


def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {
            "last_spoken_summary": "",
            "last_matched_command": "",
            "last_transcript": "",
            "voice_muted": False,
        }

    try:
        with STATE_PATH.open("r", encoding="utf-8-sig") as f:
            state = json.load(f)

        if not isinstance(state, dict):
            return {}

        state.setdefault("last_spoken_summary", "")
        state.setdefault("last_matched_command", "")
        state.setdefault("last_transcript", "")
        state.setdefault("voice_muted", False)
        return state

    except Exception:
        return {
            "last_spoken_summary": "",
            "last_matched_command": "",
            "last_transcript": "",
            "voice_muted": False,
        }


def save_state(state: dict[str, Any]) -> None:
    with STATE_PATH.open("w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def load_environment(project_root: Path) -> None:
    load_dotenv(project_root / ".env")
    load_dotenv(VOICE_DIR / ".env")


def write_session_log(event: dict[str, Any]) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    safe_event = {
        "timestamp_utc": utc_now_iso(),
        **event,
    }

    with SESSION_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(safe_event, ensure_ascii=False) + "\n")


def remove_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def normalize_text(text: str) -> str:
    text = remove_accents(text)
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text


def apply_common_stt_corrections(text: str) -> str:
    normalized = normalize_text(text)

    replacements = {
        "diagnoz": "diagnose",
        "diagnos": "diagnose",
        "diagnosis": "diagnose",
        "diagnosed": "diagnose",
        "diagnosee": "diagnose",
        "diagnose image": "diagnose immich",
        "diagnose images": "diagnose immich",
        "diagnose imich": "diagnose immich",
        "diagnose emmich": "diagnose immich",
        "diagnose emich": "diagnose immich",
        "diagnose gimmick": "diagnose immich",
        "diagnose mimic": "diagnose immich",
        "immage": "immich",
        "image": "immich",
        "images": "immich",
        "imich": "immich",
        "emmich": "immich",
        "emich": "immich",
        "gimmick": "immich",
        "mimic": "immich",
        "back end": "backend",
        "back-end": "backend",
        "front end": "frontend",
        "front-end": "frontend",
        "storagee": "storage",
        "net work": "network",
        "tail scale": "tailscale",
        "end points": "endpoints",
        "skill": "skills",
        "valid endpoints": "validate endpoints",
        "valid skills": "validate skills",
        "validation endpoints": "validate endpoints",
        "validation skills": "validate skills",
        "explane": "explain",
        "exp lain": "explain",
        "open ai": "openai",
        "open a i": "openai",
        "re peat": "repeat",
        "mutee": "mute",
        "un mute": "unmute",
    }

    corrected = normalized

    for wrong, right in replacements.items():
        corrected = corrected.replace(normalize_text(wrong), normalize_text(right))

    known_words = {
        "diagnose",
        "immich",
        "backup",
        "storage",
        "network",
        "backend",
        "frontend",
        "explain",
        "preview",
        "context",
        "openai",
        "intent",
        "run",
        "validate",
        "endpoints",
        "skills",
        "slow",
        "why",
        "is",
        "okay",
        "healthy",
        "private",
        "cloud",
        "repeat",
        "last",
        "response",
        "mute",
        "unmute",
        "voice",
        "logs",
        "history",
    }

    corrected_tokens: list[str] = []

    for token in corrected.split():
        if token in known_words:
            corrected_tokens.append(token)
            continue

        close = difflib.get_close_matches(token, list(known_words), n=1, cutoff=0.82)
        corrected_tokens.append(close[0] if close else token)

    return " ".join(corrected_tokens)


def is_blocked(transcript: str, blocked_keywords: list[str]) -> tuple[bool, str | None]:
    normalized = apply_common_stt_corrections(transcript)

    for keyword in blocked_keywords:
        if normalize_text(keyword) in normalized:
            return True, keyword

    return False, None


def score_match(transcript: str, phrase: str) -> int:
    transcript_norm = apply_common_stt_corrections(transcript)
    phrase_norm = normalize_text(phrase)

    if transcript_norm == phrase_norm:
        return 100

    if phrase_norm in transcript_norm:
        return 92

    transcript_words = set(transcript_norm.split())
    phrase_words = set(phrase_norm.split())

    if not phrase_words:
        return 0

    overlap = len(transcript_words.intersection(phrase_words))
    word_overlap_score = int((overlap / len(phrase_words)) * 75)
    sequence_score = int(difflib.SequenceMatcher(None, transcript_norm, phrase_norm).ratio() * 100)

    return max(word_overlap_score, sequence_score)


def map_phrase_to_item(
    transcript: str,
    items: dict[str, list[str]],
    minimum_score: int,
) -> tuple[str | None, int, str]:
    corrected_transcript = apply_common_stt_corrections(transcript)

    best_item: str | None = None
    best_score = 0

    for item, phrases in items.items():
        all_phrases = [item] + phrases

        for phrase in all_phrases:
            current_score = score_match(corrected_transcript, phrase)

            if current_score > best_score:
                best_score = current_score
                best_item = item

    if best_score < minimum_score:
        return None, best_score, corrected_transcript

    return best_item, best_score, corrected_transcript


def map_transcript_to_local_voice_command(transcript: str, config: dict[str, Any]) -> tuple[str | None, int, str]:
    local_commands: dict[str, list[str]] = config.get("local_voice_commands", {})
    min_score = int(config.get("minimum_match_score", 55))
    return map_phrase_to_item(transcript, local_commands, min_score)


def map_transcript_to_vetri_command(transcript: str, config: dict[str, Any]) -> tuple[str | None, int, str]:
    allowed_commands: dict[str, list[str]] = config.get("allowed_commands", {})
    min_score = int(config.get("minimum_match_score", 55))
    return map_phrase_to_item(transcript, allowed_commands, min_score)


def get_policy_for_command(
    command: str,
    config: dict[str, Any],
    policy_key: str,
    default_risk: str,
) -> dict[str, Any]:
    policies: dict[str, dict[str, Any]] = config.get(policy_key, {})

    default_policy = {
        "enabled": True,
        "risk": default_risk,
        "requires_confirmation": False,
        "description": "No description provided.",
    }

    policy = policies.get(command, default_policy)

    return {
        "enabled": bool(policy.get("enabled", default_policy["enabled"])),
        "risk": str(policy.get("risk", default_policy["risk"])).lower(),
        "requires_confirmation": bool(policy.get("requires_confirmation", default_policy["requires_confirmation"])),
        "description": str(policy.get("description", default_policy["description"])),
    }


def validate_command_policy(
    command: str,
    config: dict[str, Any],
    policy_key: str,
    default_risk: str,
) -> tuple[bool, str, dict[str, Any]]:
    policy = get_policy_for_command(
        command=command,
        config=config,
        policy_key=policy_key,
        default_risk=default_risk,
    )

    allowed_risks = {"local", "low", "medium", "high"}

    if policy["risk"] not in allowed_risks:
        return (
            False,
            f"Command '{command}' has invalid risk level '{policy['risk']}' in config.",
            policy,
        )

    if not policy["enabled"]:
        return (
            False,
            f"Command '{command}' is disabled by voice_config.json policy.",
            policy,
        )

    if policy["risk"] == "high":
        return (
            False,
            f"Command '{command}' is marked as high risk and is blocked in voice mode.",
            policy,
        )

    return True, "Command policy passed.", policy


def confirm_if_required(command: str, policy: dict[str, Any], non_interactive: bool) -> bool:
    if not policy.get("requires_confirmation", False):
        return True

    if non_interactive:
        print(f"[Vetri Voice] Confirmation required for '{command}', but this mode is non-interactive.")
        return False

    print()
    print("[Vetri Voice] Confirmation required.")
    print(f"Command: {command}")
    print(f"Risk: {policy.get('risk')}")
    print(f"Description: {policy.get('description')}")
    answer = input("Type YES to confirm execution: ").strip()

    return answer == "YES"


def record_audio(output_wav: Path, seconds: int, sample_rate: int) -> None:
    print(f"\n[Vetri Voice] Recording for {seconds} seconds...")
    print("[Vetri Voice] Speak now.")

    audio = sd.rec(
        int(seconds * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
    )
    sd.wait()

    audio = np.squeeze(audio)
    sf.write(str(output_wav), audio, sample_rate)

    print(f"[Vetri Voice] Audio saved temporarily: {output_wav}")


def transcribe_audio(client: OpenAI, wav_path: Path, model: str) -> str:
    print("[Vetri Voice] Transcribing...")

    with wav_path.open("rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model=model,
            file=audio_file,
            response_format="text",
            prompt=(
                "The user is speaking commands for a private cloud assistant named Vetri. "
                "Possible phrases include diagnose immich, diagnose backend, diagnose frontend, "
                "diagnose storage, diagnose network, diagnose backup, validate endpoints, validate skills, "
                "repeat last response, mute voice, unmute voice, show logs. "
                "Immich is spelled I M M I C H."
            ),
        )

    if isinstance(transcription, str):
        return transcription.strip()

    return str(transcription).strip()


def run_vetri_command(
    project_root: Path,
    python_command: str,
    module_name: str,
    command: str,
) -> tuple[int, str]:
    print(f"[Vetri Voice] Running safe Vetri command: {command}")
    print(f"[Vetri Voice] Module: {module_name}")
    print(f"[Vetri Voice] Working directory: {project_root}")

    process_input = f"{command}\nexit\n"

    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")

    if existing_pythonpath:
        env["PYTHONPATH"] = f"{project_root}{os.pathsep}{existing_pythonpath}"
    else:
        env["PYTHONPATH"] = str(project_root)

    result = subprocess.run(
        [python_command, "-m", module_name],
        input=process_input,
        capture_output=True,
        text=True,
        cwd=str(project_root),
        timeout=120,
        env=env,
    )

    output = ""

    if result.stdout:
        output += result.stdout

    if result.stderr:
        output += "\n[stderr]\n" + result.stderr

    return result.returncode, output.strip()


def extract_status_summary(output: str) -> str | None:
    if not output.strip():
        return None

    clean_output = output.strip()

    endpoint_validation_match = re.search(
        r"Backend Endpoint Validation.*?Total:\s*(\d+).*?Reachable:\s*(\d+).*?Failed:\s*(\d+)",
        clean_output,
        re.IGNORECASE | re.DOTALL,
    )

    if endpoint_validation_match:
        total = endpoint_validation_match.group(1)
        reachable = endpoint_validation_match.group(2)
        failed = endpoint_validation_match.group(3)

        if failed == "0":
            return (
                f"Backend endpoint validation completed. "
                f"All {reachable} out of {total} endpoints are reachable. "
                "No failed endpoints."
            )

        return (
            f"Backend endpoint validation completed. "
            f"{reachable} out of {total} endpoints are reachable. "
            f"{failed} endpoint checks failed. Please review the terminal output."
        )

    skill_validation_patterns = [
        r"Skill.*?Validation.*?Total:\s*(\d+).*?Passed:\s*(\d+).*?Failed:\s*(\d+)",
        r"Skill.*?Validation.*?Total:\s*(\d+).*?Valid:\s*(\d+).*?Failed:\s*(\d+)",
        r"Skill.*?Validation.*?Total:\s*(\d+).*?OK:\s*(\d+).*?Failed:\s*(\d+)",
        r"Skills?.*?Total:\s*(\d+).*?Passed:\s*(\d+).*?Failed:\s*(\d+)",
    ]

    for pattern in skill_validation_patterns:
        skill_validation_match = re.search(
            pattern,
            clean_output,
            re.IGNORECASE | re.DOTALL,
        )

        if skill_validation_match:
            total = skill_validation_match.group(1)
            passed = skill_validation_match.group(2)
            failed = skill_validation_match.group(3)

            if failed == "0":
                return (
                    f"Skill validation completed. "
                    f"All {passed} out of {total} skills passed. "
                    "No failed skills."
                )

            return (
                f"Skill validation completed. "
                f"{passed} out of {total} skills passed. "
                f"{failed} skills failed. Please review the terminal output."
            )

    if re.search(r"Skill.*?Validation", clean_output, re.IGNORECASE):
        ok_count = len(re.findall(r"\[OK\]", clean_output, re.IGNORECASE))
        fail_count = len(re.findall(r"\[FAIL\]", clean_output, re.IGNORECASE))
        total_count = ok_count + fail_count

        if total_count > 0:
            if fail_count == 0:
                return (
                    f"Skill validation completed. "
                    f"All {ok_count} checked skills passed. "
                    "No failed skills."
                )

            return (
                f"Skill validation completed. "
                f"{ok_count} skills passed and {fail_count} skills failed. "
                "Please review the terminal output."
            )

    service_match = re.search(r"Service:\s*(.+)", clean_output, re.IGNORECASE)
    status_match = re.search(r"Overall status:\s*(.+)", clean_output, re.IGNORECASE)
    failed_steps_match = re.search(r"Failed steps:\s*(\d+)", clean_output, re.IGNORECASE)
    message_match = re.search(r"Message:\s*(.+)", clean_output, re.IGNORECASE)

    service = service_match.group(1).strip() if service_match else "The requested service"
    status = status_match.group(1).strip() if status_match else None
    failed_steps = failed_steps_match.group(1).strip() if failed_steps_match else None
    message = message_match.group(1).strip() if message_match else None

    if status:
        if status.lower() == "healthy":
            return (
                f"{service} diagnosis completed. "
                f"Overall status is healthy. "
                f"Failed steps: {failed_steps or 'zero'}. "
                "No immediate action is needed."
            )

        if status.lower() in {"warning", "degraded"}:
            return (
                f"{service} diagnosis completed. "
                f"Overall status is {status}. "
                f"Failed steps: {failed_steps or 'unknown'}. "
                "Attention may be needed. Please review the terminal output."
            )

        if status.lower() in {"failed", "unhealthy", "error"}:
            return (
                f"{service} diagnosis completed. "
                f"Overall status is {status}. "
                f"Failed steps: {failed_steps or 'unknown'}. "
                "This needs attention. Please review the terminal output."
            )

        return (
            f"{service} diagnosis completed. "
            f"Overall status is {status}. "
            f"Failed steps: {failed_steps or 'unknown'}."
        )

    if message:
        return f"Vetri completed the command. Result: {message}"

    ok_title_match = re.search(r"\[OK\]\s*(.+)", clean_output, re.IGNORECASE)
    fail_title_match = re.search(r"\[FAIL\]\s*(.+)", clean_output, re.IGNORECASE)

    if ok_title_match:
        title = ok_title_match.group(1).strip()
        ok_count = len(re.findall(r"\[OK\]", clean_output, re.IGNORECASE))
        fail_count = len(re.findall(r"\[FAIL\]", clean_output, re.IGNORECASE))

        if fail_count == 0:
            if ok_count > 1:
                return f"{title} completed successfully. {ok_count} checks passed and no failures were found."

            return f"{title} completed successfully. No failures were found."

        return f"{title} completed with {ok_count} successful checks and {fail_count} failed checks."

    if fail_title_match:
        title = fail_title_match.group(1).strip()
        fail_count = len(re.findall(r"\[FAIL\]", clean_output, re.IGNORECASE))
        return f"{title} completed with {fail_count} failure indicators. Please review the terminal output."

    openai_markers = [
        "OpenAI",
        "Assessment:",
        "Reasoning:",
        "Recommended next steps:",
        "Possible causes",
    ]

    if any(marker.lower() in clean_output.lower() for marker in openai_markers):
        lines = []

        for raw_line in clean_output.splitlines():
            line = raw_line.strip()

            if not line:
                continue

            lower = line.lower()

            if lower.startswith("vetri >"):
                continue

            if lower.startswith("type "):
                continue

            if lower.startswith("prefix "):
                continue

            if lower.startswith("example:"):
                continue

            if "vetri ai - phase" in lower:
                continue

            if "openai-assisted read-only execution" in lower:
                continue

            if "local validation required" in lower:
                continue

            if line.startswith("="):
                continue

            lines.append(line)

        compact = " ".join(lines)
        compact = re.sub(r"\s+", " ", compact).strip()

        if compact:
            if len(compact) > 420:
                compact = compact[:420].rsplit(" ", 1)[0] + "."
            return compact

    return None


def clean_output_for_speech(output: str, max_chars: int) -> str:
    summary = extract_status_summary(output)

    if summary:
        return summary

    if not output.strip():
        return "The command completed, but I did not receive any output."

    lines = output.splitlines()

    useful_lines: list[str] = []
    skip_prefixes = (
        "vetri >",
        "[vetri voice]",
        "====",
        "type ",
        "prefix ",
        "example:",
    )

    for line in lines:
        clean = line.strip()

        if not clean:
            continue

        if clean.lower().startswith(skip_prefixes):
            continue

        if "Vetri AI - Phase" in clean:
            continue

        useful_lines.append(clean)

    cleaned = " ".join(useful_lines)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if not cleaned:
        cleaned = output.strip().replace("\n", " ")

    if len(cleaned) > max_chars:
        cleaned = cleaned[:max_chars].rsplit(" ", 1)[0] + "."

    return cleaned


def speak_text(client: OpenAI, text: str, model: str, voice: str, muted: bool) -> None:
    if muted:
        print("[Vetri Voice] Voice output is muted. Skipping speech playback.")
        return

    print("[Vetri Voice] Speaking response...")

    speech_path = VOICE_DIR / "last_response.mp3"

    with client.audio.speech.with_streaming_response.create(
        model=model,
        voice=voice,
        input=text,
        instructions=(
            "Speak like Vetri, a calm, technical, private cloud assistant. "
            "Be concise, confident, and clear."
        ),
    ) as response:
        response.stream_to_file(speech_path)

    if sys.platform.startswith("win"):
        os.startfile(str(speech_path))
    elif sys.platform == "darwin":
        subprocess.run(["open", str(speech_path)], check=False)
    else:
        subprocess.run(["xdg-open", str(speech_path)], check=False)


def show_recent_logs(limit: int = 10) -> None:
    print("\n========================================")
    print(" Vetri Voice - Recent Session Logs")
    print("========================================")

    if not SESSION_LOG_PATH.exists():
        print("No voice session log exists yet.")
        return

    lines = SESSION_LOG_PATH.read_text(encoding="utf-8").splitlines()
    recent = lines[-limit:]

    for line in recent:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            print(line)
            continue

        print()
        print(f"Time:      {event.get('timestamp_utc')}")
        print(f"Version:   {event.get('version')}")
        print(f"Mode:      {event.get('mode') or event.get('command_type')}")
        print(f"Heard:     {event.get('transcript')}")
        print(f"Corrected: {event.get('corrected_transcript')}")
        print(f"Command:   {event.get('matched_command')}")
        print(f"Risk:      {event.get('policy_risk')}")
        print(f"Score:     {event.get('confidence')}")
        print(f"Blocked:   {event.get('blocked')}")
        print(f"Return:    {event.get('return_code')}")
        print(f"Summary:   {event.get('spoken_summary')}")

    print("\n========================================")


def handle_local_voice_command(
    local_command: str,
    state: dict[str, Any],
    client: OpenAI | None,
    config: dict[str, Any],
    allow_speech: bool,
) -> str:
    if local_command == "repeat last response":
        last_summary = state.get("last_spoken_summary", "")

        if not last_summary:
            return "There is no previous spoken response to repeat."

        if client is not None and allow_speech:
            speak_text(
                client=client,
                text=last_summary,
                model=config.get("text_to_speech_model", "gpt-4o-mini-tts"),
                voice=config.get("tts_voice", "coral"),
                muted=bool(state.get("voice_muted", False)),
            )

        return last_summary

    if local_command == "mute voice":
        state["voice_muted"] = True
        save_state(state)
        return "Voice output is now muted. I will still print responses in the terminal."

    if local_command == "unmute voice":
        state["voice_muted"] = False
        save_state(state)
        return "Voice output is now unmuted."

    if local_command == "show logs":
        show_recent_logs(limit=10)
        return "Recent voice logs are now shown in the terminal."

    return "Local voice command recognized, but no handler is available."


def print_policy_table(config: dict[str, Any]) -> None:
    print("\n========================================")
    print(" Vetri Voice V0G - Command Policy")
    print("========================================")

    command_policy: dict[str, dict[str, Any]] = config.get("command_policy", {})
    local_policy: dict[str, dict[str, Any]] = config.get("local_command_policy", {})

    print("\nLocal voice commands:")
    for command in sorted(config.get("local_voice_commands", {}).keys()):
        policy = get_policy_for_command(command, config, "local_command_policy", "local")
        print(
            f"- {command} | enabled={policy['enabled']} | "
            f"risk={policy['risk']} | confirm={policy['requires_confirmation']}"
        )

    print("\nVetri Phase 3 commands:")
    for command in sorted(config.get("allowed_commands", {}).keys()):
        policy = get_policy_for_command(command, config, "command_policy", "low")
        print(
            f"- {command} | enabled={policy['enabled']} | "
            f"risk={policy['risk']} | confirm={policy['requires_confirmation']}"
        )

    missing_policies = []

    for command in config.get("allowed_commands", {}).keys():
        if command not in command_policy:
            missing_policies.append(command)

    for command in config.get("local_voice_commands", {}).keys():
        if command not in local_policy:
            missing_policies.append(command)

    if missing_policies:
        print("\nCommands missing explicit policy:")
        for command in missing_policies:
            print(f"- {command}")
    else:
        print("\nAll commands have explicit policies.")

    print("\n========================================")


def print_header(state: dict[str, Any]) -> None:
    muted_status = "muted" if state.get("voice_muted", False) else "unmuted"

    print("\n========================================")
    print(" Vetri Voice V0G - Safe Push-to-Talk")
    print("========================================")
    print("Mode: Voice input -> policy-checked safe Vetri command")
    print("Execution: python -m vetri_ai.main")
    print("Added: command policy hardening")
    print(f"Voice output: {muted_status}")
    print("Log file: voice\\logs\\voice_sessions.jsonl")
    print("Policy file: voice\\voice_config.json")
    print("Blocked: Home Assistant control, Spotify control, restarts, writes")
    print("Try: diagnose immich | is my backend okay | repeat last response | mute voice")
    print("Type logs to view logs. Type q to quit.")
    print("========================================\n")


def smoke_test(config: dict[str, Any]) -> None:
    print("\n========================================")
    print(" Vetri Voice V0G - Local Smoke Test")
    print("========================================")

    test_phrases = [
        "Diagnóz Immich.",
        "diagnose image",
        "is immich healthy",
        "is my backend okay",
        "check my private cloud",
        "are endpoints working",
        "repeat last response",
        "mute voice",
        "unmute voice",
        "show logs",
        "turn off home assistant light",
        "restart immich",
    ]

    for phrase in test_phrases:
        blocked, blocked_keyword = is_blocked(phrase, config.get("blocked_keywords", []))

        local_command, local_score, corrected_local = map_transcript_to_local_voice_command(phrase, config)
        vetri_command, vetri_score, corrected_vetri = map_transcript_to_vetri_command(phrase, config)

        corrected = corrected_vetri or corrected_local

        print(f"\nInput:     {phrase}")
        print(f"Corrected: {corrected}")

        if blocked:
            print(f"Result:    BLOCKED due to keyword: {blocked_keyword}")
            continue

        if local_command and local_score >= vetri_score:
            allowed, message, policy = validate_command_policy(
                command=local_command,
                config=config,
                policy_key="local_command_policy",
                default_risk="local",
            )
            print(f"Result:    LOCAL -> {local_command} | score={local_score}")
            print(f"Policy:    allowed={allowed} | risk={policy['risk']} | message={message}")
            continue

        if vetri_command:
            allowed, message, policy = validate_command_policy(
                command=vetri_command,
                config=config,
                policy_key="command_policy",
                default_risk="low",
            )
            print(f"Result:    VETRI -> {vetri_command} | score={vetri_score}")
            print(f"Policy:    allowed={allowed} | risk={policy['risk']} | message={message}")
            continue

        print(f"Result:    NO SAFE MATCH | best_score={max(local_score, vetri_score)}")

    print("\n========================================")
    print(" Smoke test completed.")
    print("========================================")


def text_test_mode(config: dict[str, Any], text_command: str) -> None:
    project_root = Path(config["project_root"])
    python_command = config.get("python_command", "python")
    vetri_module = config.get("vetri_module", "vetri_ai.main")

    load_environment(project_root)

    state = load_state()
    started_at = time.time()

    transcript = text_command
    corrected_transcript = ""
    matched_command: str | None = None
    command_type = "none"
    confidence = 0
    blocked = False
    blocked_keyword: str | None = None
    return_code: int | None = None
    spoken = ""
    error_message: str | None = None
    policy_risk: str | None = None
    policy_description: str | None = None

    print("\n========================================")
    print(" Vetri Voice V0G - Text Test Mode")
    print("========================================")
    print("Mode: typed text -> policy-checked safe Vetri routing")
    print("No microphone used.")
    print("No OpenAI speech-to-text used.")
    print("No text-to-speech playback used.")
    print("========================================")
    print(f"Input text: {transcript}")

    try:
        blocked, blocked_keyword = is_blocked(
            transcript=transcript,
            blocked_keywords=config.get("blocked_keywords", []),
        )

        local_command, local_score, corrected_local = map_transcript_to_local_voice_command(transcript, config)
        vetri_command, vetri_score, corrected_vetri = map_transcript_to_vetri_command(transcript, config)

        corrected_transcript = corrected_vetri or corrected_local

        print(f"Corrected transcript: {corrected_transcript}")

        if blocked:
            spoken = (
                f"I heard a blocked action related to '{blocked_keyword}'. "
                "Voice mode is limited to safe read-only Vetri Phase 3 commands."
            )

            print(f"[BLOCKED] {spoken}")
            return

        if local_command and local_score >= vetri_score:
            matched_command = local_command
            confidence = local_score
            command_type = "local_voice"

            allowed, policy_message, policy = validate_command_policy(
                command=local_command,
                config=config,
                policy_key="local_command_policy",
                default_risk="local",
            )
            policy_risk = policy["risk"]
            policy_description = policy["description"]

            print(f"Matched local command: {local_command}")
            print(f"Confidence score: {confidence}")
            print(f"Policy: {policy_message}")

            if not allowed:
                spoken = policy_message
                print(f"[POLICY BLOCK] {spoken}")
                return

            if not confirm_if_required(local_command, policy, non_interactive=True):
                spoken = f"Command '{local_command}' was not executed because confirmation was required."
                print(f"[CONFIRMATION BLOCK] {spoken}")
                return

            spoken = handle_local_voice_command(
                local_command=local_command,
                state=state,
                client=None,
                config=config,
                allow_speech=False,
            )
            print(spoken)
            return

        if not vetri_command:
            confidence = max(local_score, vetri_score)
            spoken = (
                "I could not safely match that to an approved Vetri command. "
                "Try diagnose backend, diagnose immich, validate endpoints, or repeat last response."
            )

            print(f"[NO SAFE MATCH] Score: {confidence}")
            print(spoken)
            return

        matched_command = vetri_command
        confidence = vetri_score
        command_type = "vetri_phase3"

        allowed, policy_message, policy = validate_command_policy(
            command=vetri_command,
            config=config,
            policy_key="command_policy",
            default_risk="low",
        )
        policy_risk = policy["risk"]
        policy_description = policy["description"]

        print(f"Matched Vetri command: {vetri_command}")
        print(f"Confidence score: {confidence}")
        print(f"Policy: {policy_message}")

        if not allowed:
            spoken = policy_message
            print(f"[POLICY BLOCK] {spoken}")
            return

        if not confirm_if_required(vetri_command, policy, non_interactive=True):
            spoken = f"Command '{vetri_command}' was not executed because confirmation was required."
            print(f"[CONFIRMATION BLOCK] {spoken}")
            return

        print(f"Confirmed safe execution: {vetri_command}")

        return_code, output = run_vetri_command(
            project_root=project_root,
            python_command=python_command,
            module_name=vetri_module,
            command=vetri_command,
        )

        print("\n========== Vetri CLI Output ==========")
        print(output if output else "[No output]")
        print("======================================")

        if return_code != 0:
            spoken = (
                "The Vetri command returned an error. "
                "Please check the terminal output for details."
            )
        else:
            spoken = clean_output_for_speech(
                output=output,
                max_chars=int(config.get("max_spoken_chars", 450)),
            )

        print(f"\n[Vetri Voice] Text-mode spoken summary: {spoken}")

        state["last_spoken_summary"] = spoken
        state["last_matched_command"] = matched_command or ""
        state["last_transcript"] = transcript
        save_state(state)

    except Exception as exc:
        error_message = str(exc)
        spoken = "The text test session failed. Please check the terminal output."
        print(f"[Vetri Voice] ERROR during text test: {error_message}")

    finally:
        duration_seconds = round(time.time() - started_at, 3)

        write_session_log(
            {
                "version": "V0G",
                "mode": "text_test",
                "command_type": command_type,
                "transcript": transcript,
                "corrected_transcript": corrected_transcript,
                "matched_command": matched_command,
                "confidence": confidence,
                "blocked": blocked,
                "blocked_keyword": blocked_keyword,
                "policy_risk": policy_risk,
                "policy_description": policy_description,
                "return_code": return_code,
                "spoken_summary": spoken,
                "voice_muted": bool(state.get("voice_muted", False)),
                "error": error_message,
                "duration_seconds": duration_seconds,
            }
        )

        print(f"[Vetri Voice] Text test session logged: {SESSION_LOG_PATH}")


def interactive_loop(config: dict[str, Any]) -> None:
    project_root = Path(config["project_root"])
    python_command = config.get("python_command", "python")
    vetri_module = config.get("vetri_module", "vetri_ai.main")

    load_environment(project_root)

    if not os.getenv("OPENAI_API_KEY"):
        raise EnvironmentError(
            "OPENAI_API_KEY not found.\n"
            "Add it to Z:\\HomeLLM\\.env as:\n"
            "OPENAI_API_KEY=your_key_here"
        )

    client = OpenAI()
    state = load_state()

    print_header(state)

    while True:
        user_choice = input("\nPress Enter to record, type logs/repeat/mute/unmute/policy, or type q to quit: ").strip().lower()

        if user_choice in {"q", "quit", "exit"}:
            print("[Vetri Voice] Exiting.")
            break

        if user_choice in {"log", "logs", "history"}:
            show_recent_logs(limit=10)
            continue

        if user_choice in {"policy", "policies", "show policy", "show policies"}:
            print_policy_table(config)
            continue

        if user_choice in {"repeat", "repeat last", "repeat last response"}:
            local_spoken = handle_local_voice_command("repeat last response", state, client, config, allow_speech=True)
            print(f"[Vetri Voice] {local_spoken}")
            continue

        if user_choice in {"mute", "mute voice"}:
            local_spoken = handle_local_voice_command("mute voice", state, client, config, allow_speech=True)
            print(f"[Vetri Voice] {local_spoken}")
            continue

        if user_choice in {"unmute", "unmute voice"}:
            local_spoken = handle_local_voice_command("unmute voice", state, client, config, allow_speech=True)
            print(f"[Vetri Voice] {local_spoken}")
            continue

        started_at = time.time()

        transcript = ""
        corrected_transcript = ""
        matched_command: str | None = None
        command_type = "none"
        confidence = 0
        blocked = False
        blocked_keyword: str | None = None
        return_code: int | None = None
        spoken = ""
        error_message: str | None = None
        policy_risk: str | None = None
        policy_description: str | None = None

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                wav_path = Path(tmpdir) / "vetri_voice_input.wav"

                record_audio(
                    output_wav=wav_path,
                    seconds=int(config.get("record_seconds", 5)),
                    sample_rate=int(config.get("sample_rate", 16000)),
                )

                transcript = transcribe_audio(
                    client=client,
                    wav_path=wav_path,
                    model=config.get("speech_to_text_model", "gpt-4o-mini-transcribe"),
                )

            print(f"\n[Vetri Voice] Heard: {transcript}")

            blocked, blocked_keyword = is_blocked(
                transcript=transcript,
                blocked_keywords=config.get("blocked_keywords", []),
            )

            local_command, local_score, corrected_local = map_transcript_to_local_voice_command(transcript, config)
            vetri_command, vetri_score, corrected_vetri = map_transcript_to_vetri_command(transcript, config)

            corrected_transcript = corrected_vetri or corrected_local

            print(f"[Vetri Voice] Corrected transcript: {corrected_transcript}")

            if blocked:
                spoken = (
                    f"I heard a blocked action related to '{blocked_keyword}'. "
                    "Voice mode is limited to safe read-only Vetri Phase 3 commands."
                )
                print(f"[Vetri Voice] BLOCKED: {spoken}")

                speak_text(
                    client=client,
                    text=spoken,
                    model=config.get("text_to_speech_model", "gpt-4o-mini-tts"),
                    voice=config.get("tts_voice", "coral"),
                    muted=bool(state.get("voice_muted", False)),
                )

                continue

            if local_command and local_score >= vetri_score:
                matched_command = local_command
                confidence = local_score
                command_type = "local_voice"

                allowed, policy_message, policy = validate_command_policy(
                    command=local_command,
                    config=config,
                    policy_key="local_command_policy",
                    default_risk="local",
                )
                policy_risk = policy["risk"]
                policy_description = policy["description"]

                print(f"[Vetri Voice] Matched local voice command: {local_command}")
                print(f"[Vetri Voice] Match confidence score: {confidence}")
                print(f"[Vetri Voice] Policy: {policy_message}")

                if not allowed:
                    spoken = policy_message
                    print(f"[Vetri Voice] POLICY BLOCK: {spoken}")
                    speak_text(
                        client=client,
                        text=spoken,
                        model=config.get("text_to_speech_model", "gpt-4o-mini-tts"),
                        voice=config.get("tts_voice", "coral"),
                        muted=bool(state.get("voice_muted", False)),
                    )
                    continue

                if not confirm_if_required(local_command, policy, non_interactive=False):
                    spoken = f"Command '{local_command}' was not executed because confirmation was not provided."
                    print(f"[Vetri Voice] CONFIRMATION BLOCK: {spoken}")
                    speak_text(
                        client=client,
                        text=spoken,
                        model=config.get("text_to_speech_model", "gpt-4o-mini-tts"),
                        voice=config.get("tts_voice", "coral"),
                        muted=bool(state.get("voice_muted", False)),
                    )
                    continue

                spoken = handle_local_voice_command(local_command, state, client, config, allow_speech=True)

                if local_command not in {"repeat last response", "show logs"}:
                    print(f"[Vetri Voice] {spoken}")
                    speak_text(
                        client=client,
                        text=spoken,
                        model=config.get("text_to_speech_model", "gpt-4o-mini-tts"),
                        voice=config.get("tts_voice", "coral"),
                        muted=bool(state.get("voice_muted", False)),
                    )

                continue

            if not vetri_command:
                confidence = max(local_score, vetri_score)
                spoken = (
                    "I could not safely match that to an approved Vetri command. "
                    "Try saying diagnose backend, diagnose immich, validate endpoints, or repeat last response."
                )
                print(f"[Vetri Voice] No safe match. Score: {confidence}")

                speak_text(
                    client=client,
                    text=spoken,
                    model=config.get("text_to_speech_model", "gpt-4o-mini-tts"),
                    voice=config.get("tts_voice", "coral"),
                    muted=bool(state.get("voice_muted", False)),
                )

                continue

            matched_command = vetri_command
            confidence = vetri_score
            command_type = "vetri_phase3"

            allowed, policy_message, policy = validate_command_policy(
                command=vetri_command,
                config=config,
                policy_key="command_policy",
                default_risk="low",
            )
            policy_risk = policy["risk"]
            policy_description = policy["description"]

            print(f"[Vetri Voice] Matched Vetri command: {vetri_command}")
            print(f"[Vetri Voice] Match confidence score: {confidence}")
            print(f"[Vetri Voice] Policy: {policy_message}")

            if not allowed:
                spoken = policy_message
                print(f"[Vetri Voice] POLICY BLOCK: {spoken}")
                speak_text(
                    client=client,
                    text=spoken,
                    model=config.get("text_to_speech_model", "gpt-4o-mini-tts"),
                    voice=config.get("tts_voice", "coral"),
                    muted=bool(state.get("voice_muted", False)),
                )
                continue

            if not confirm_if_required(vetri_command, policy, non_interactive=False):
                spoken = f"Command '{vetri_command}' was not executed because confirmation was not provided."
                print(f"[Vetri Voice] CONFIRMATION BLOCK: {spoken}")
                speak_text(
                    client=client,
                    text=spoken,
                    model=config.get("text_to_speech_model", "gpt-4o-mini-tts"),
                    voice=config.get("tts_voice", "coral"),
                    muted=bool(state.get("voice_muted", False)),
                )
                continue

            print(f"[Vetri Voice] Confirmed safe execution: {vetri_command}")

            return_code, output = run_vetri_command(
                project_root=project_root,
                python_command=python_command,
                module_name=vetri_module,
                command=vetri_command,
            )

            print("\n========== Vetri CLI Output ==========")
            print(output if output else "[No output]")
            print("======================================")

            if return_code != 0:
                spoken = (
                    "The Vetri command returned an error. "
                    "Please check the terminal output for details."
                )
            else:
                spoken = clean_output_for_speech(
                    output=output,
                    max_chars=int(config.get("max_spoken_chars", 450)),
                )

            print(f"[Vetri Voice] Spoken summary: {spoken}")

            state["last_spoken_summary"] = spoken
            state["last_matched_command"] = matched_command or ""
            state["last_transcript"] = transcript
            save_state(state)

            speak_text(
                client=client,
                text=spoken,
                model=config.get("text_to_speech_model", "gpt-4o-mini-tts"),
                voice=config.get("tts_voice", "coral"),
                muted=bool(state.get("voice_muted", False)),
            )

        except Exception as exc:
            error_message = str(exc)
            print(f"[Vetri Voice] ERROR during session: {error_message}")
            spoken = "The voice session failed. Please check the terminal output."

        finally:
            duration_seconds = round(time.time() - started_at, 3)

            write_session_log(
                {
                    "version": "V0G",
                    "command_type": command_type,
                    "transcript": transcript,
                    "corrected_transcript": corrected_transcript,
                    "matched_command": matched_command,
                    "confidence": confidence,
                    "blocked": blocked,
                    "blocked_keyword": blocked_keyword,
                    "policy_risk": policy_risk,
                    "policy_description": policy_description,
                    "return_code": return_code,
                    "spoken_summary": spoken,
                    "voice_muted": bool(state.get("voice_muted", False)),
                    "error": error_message,
                    "duration_seconds": duration_seconds,
                }
            )

            print(f"[Vetri Voice] Session logged: {SESSION_LOG_PATH}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Vetri Voice V0G")
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run local matching tests without recording audio or calling OpenAI.",
    )
    parser.add_argument(
        "--show-logs",
        action="store_true",
        help="Show recent voice session logs.",
    )
    parser.add_argument(
        "--show-policy",
        action="store_true",
        help="Show configured command policies.",
    )
    parser.add_argument(
        "--text",
        type=str,
        default=None,
        help="Run a typed command through the same safe Vetri voice router without microphone or STT.",
    )
    args = parser.parse_args()

    config = load_config()

    if args.smoke_test:
        smoke_test(config)
        return

    if args.show_logs:
        show_recent_logs(limit=10)
        return

    if args.show_policy:
        print_policy_table(config)
        return

    if args.text is not None:
        text_test_mode(config, args.text)
        return

    interactive_loop(config)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[Vetri Voice] Stopped by user.")
    except Exception as exc:
        print(f"\n[Vetri Voice] ERROR: {exc}")
        sys.exit(1)
