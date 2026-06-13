from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path
from typing import Any

import numpy as np
import sounddevice as sd
import soundfile as sf
from dotenv import load_dotenv
from openai import OpenAI


VOICE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = VOICE_DIR.parent
WAKE_CONFIG_PATH = VOICE_DIR / "wake_config.json"
VOICE_STATE_PATH = VOICE_DIR / "voice_state.json"
LAST_WAKE_RESPONSE_PATH = VOICE_DIR / "last_wake_response.mp3"


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return default

    try:
        with path.open("r", encoding="utf-8-sig") as f:
            data = json.load(f)

        if isinstance(data, dict):
            return data

        return default

    except Exception:
        return default


def load_config() -> dict[str, Any]:
    default = {
        "project_root": str(PROJECT_ROOT),
        "python_command": "python",
        "wake_phrases": ["hey vetri", "vetri"],
        "wake_record_seconds": 2.5,
        "command_record_seconds": 5,
        "sample_rate": 16000,
        "speech_to_text_model": "gpt-4o-mini-transcribe",
        "text_to_speech_model": "gpt-4o-mini-tts",
        "tts_voice": "coral",
        "wake_cooldown_seconds": 1.5,
        "max_empty_wake_transcripts_before_hint": 8,
        "speak_wake_ack": True,
        "wake_ack_text": "Yes Ashva, I am listening.",
        "command_prompt": "The user is speaking a Vetri private cloud command.",
        "wake_prompt": "The user may say Hey Vetri or Vetri.",
    }

    config = load_json(WAKE_CONFIG_PATH, default)

    for key, value in default.items():
        config.setdefault(key, value)

    return config


def load_voice_state() -> dict[str, Any]:
    return load_json(
        VOICE_STATE_PATH,
        {
            "last_spoken_summary": "",
            "last_matched_command": "",
            "last_transcript": "",
            "voice_muted": False,
        },
    )


def load_environment(project_root: Path) -> None:
    load_dotenv(project_root / ".env")
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


def has_wake_phrase(transcript: str, wake_phrases: list[str]) -> bool:
    normalized = normalize_text(transcript)

    if not normalized:
        return False

    for phrase in wake_phrases:
        phrase_norm = normalize_text(phrase)

        if phrase_norm and phrase_norm in normalized:
            return True

    # Extra tolerance for common STT variations.
    tolerant_phrases = [
        "hey v3",
        "hey victory",
        "hey vetri",
        "vetri",
        "vetrie",
        "vettery",
        "vettree",
        "vetry",
    ]

    return any(item in normalized for item in tolerant_phrases)


def play_beep() -> None:
    if sys.platform.startswith("win"):
        try:
            import winsound

            winsound.Beep(880, 120)
            winsound.Beep(1100, 120)
        except Exception:
            print("\a", end="")
    else:
        print("\a", end="")


def record_audio(output_wav: Path, seconds: float, sample_rate: int, label: str) -> float:
    print(f"[Vetri Wake] Recording {label} for {seconds} seconds...")

    audio = sd.rec(
        int(seconds * sample_rate),
        samplerate=sample_rate,
        channels=1,
        dtype="float32",
    )
    sd.wait()

    audio = np.squeeze(audio)

    # RMS is used to detect silence/noise-only recordings before calling STT.
    try:
        rms = float(np.sqrt(np.mean(np.square(audio))))
    except Exception:
        rms = 0.0

    sf.write(str(output_wav), audio, sample_rate)

    print(f"[Vetri Wake] Audio level RMS: {rms:.6f}")
    return rms


def transcribe_audio(client: OpenAI, wav_path: Path, model: str, prompt: str) -> str:
    with wav_path.open("rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model=model,
            file=audio_file,
            response_format="text",
            prompt=prompt,
        )

    if isinstance(transcription, str):
        return transcription.strip()

    return str(transcription).strip()


def speak_text(client: OpenAI, text: str, config: dict[str, Any]) -> None:
    state = load_voice_state()

    if state.get("voice_muted", False):
        print("[Vetri Wake] Voice is muted in voice_state.json. Skipping speech.")
        return

    print(f"[Vetri Wake] Speaking: {text}")

    with client.audio.speech.with_streaming_response.create(
        model=config.get("text_to_speech_model", "gpt-4o-mini-tts"),
        voice=config.get("tts_voice", "coral"),
        input=text,
        instructions=(
            "Speak like Vetri, a calm, technical, private cloud assistant. "
            "Keep it short and clear."
        ),
    ) as response:
        response.stream_to_file(LAST_WAKE_RESPONSE_PATH)

    if sys.platform.startswith("win"):
        os.startfile(str(LAST_WAKE_RESPONSE_PATH))
    elif sys.platform == "darwin":
        subprocess.run(["open", str(LAST_WAKE_RESPONSE_PATH)], check=False)
    else:
        subprocess.run(["xdg-open", str(LAST_WAKE_RESPONSE_PATH)], check=False)


def extract_summary_from_voice_cli_output(output: str) -> str:
    patterns = [
        r"\[Vetri Voice\] Text-mode spoken summary:\s*(.+)",
        r"\[Vetri Voice\] Spoken summary:\s*(.+)",
        r"Repeated summary:\s*(.+)",
        r"\[BLOCKED\]\s*(.+)",
        r"\[POLICY BLOCK\]\s*(.+)",
        r"\[CONFIRMATION BLOCK\]\s*(.+)",
        r"\[NO SAFE MATCH\].*?\n(.+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, output, re.IGNORECASE | re.DOTALL)

        if match:
            summary = match.group(1).strip()
            summary = summary.splitlines()[0].strip()

            if summary:
                return summary

    lines = []

    for raw_line in output.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        lower = line.lower()

        if lower.startswith("=========="):
            continue

        if lower.startswith("vetri voice v"):
            continue

        if lower.startswith("mode:"):
            continue

        if lower.startswith("no microphone"):
            continue

        if lower.startswith("no openai"):
            continue

        if lower.startswith("no text-to-speech"):
            continue

        if lower.startswith("input text:"):
            continue

        if lower.startswith("corrected transcript:"):
            continue

        if lower.startswith("matched"):
            continue

        if lower.startswith("confidence"):
            continue

        if lower.startswith("policy:"):
            continue

        if lower.startswith("[vetri voice] text test session logged"):
            continue

        lines.append(line)

    compact = " ".join(lines)
    compact = re.sub(r"\s+", " ", compact).strip()

    if not compact:
        return "The command finished, but I could not extract a clean summary."

    if len(compact) > 350:
        compact = compact[:350].rsplit(" ", 1)[0] + "."

    return compact


def is_home_assistant_control_phrase(text: str) -> bool:
    normalized = normalize_text(text)

    control_indicators = [
        "turn on",
        "turn off",
        "switch on",
        "switch off",
        "start",
        "stop",
    ]

    blocked_high_risk = [
        "unlock",
        "lock",
        "open",
        "close",
        "restart",
        "reboot",
        "shutdown",
        "delete",
        "remove",
        "set temperature",
        "change temperature",
    ]

    if any(item in normalized for item in blocked_high_risk):
        return True

    return any(item in normalized for item in control_indicators)


def extract_summary_from_home_assistant_control_output(output: str) -> str:
    action_match = re.search(r"Action:\s*(turn_on|turn_off)", output, re.IGNORECASE)
    entity_match = re.search(r"Entity:\s*(.+)", output, re.IGNORECASE)
    entity_id_match = re.search(r"Entity ID:\s*(.+)", output, re.IGNORECASE)
    status_match = re.search(r"Status code:\s*(\d+)", output, re.IGNORECASE)
    dry_run_match = re.search(r"Dry run successful\..+?No device was changed\.", output, re.IGNORECASE)

    action = action_match.group(1).strip() if action_match else ""
    entity = entity_match.group(1).strip() if entity_match else "the selected device"
    entity_id = entity_id_match.group(1).strip() if entity_id_match else ""
    status_code = status_match.group(1).strip() if status_match else ""

    friendly_action = {
        "turn_on": "turned on",
        "turn_off": "turned off",
    }.get(action, action)

    if dry_run_match:
        return f"Dry run successful. I would have {friendly_action} {entity}, but no device was changed."

    if "BACKEND LIVE REQUEST SENT" in output and status_code == "200":
        return f"Done. I {friendly_action} {entity} through the Vetri backend."

    if "BACKEND LIVE FAILED SAFELY" in output:
        return f"I could not control {entity}. The backend live request failed safely, and no direct Home Assistant call was made from Windows."

    if "LIVE POLICY BLOCK" in output:
        return f"I blocked this Home Assistant action because the matched entity is not enabled for live voice control."

    if "POLICY BLOCK" in output:
        return f"I blocked this Home Assistant action by policy."

    if "AMBIGUOUS" in output:
        return "I found more than one matching Home Assistant device. Please use a more specific name."

    if "NO MATCH" in output:
        return "I could not find a matching Home Assistant device for that command."

    if "BLOCKED" in output:
        return "I blocked that Home Assistant action because it is not allowed from voice control."

    lines = []

    for raw_line in output.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        if line.startswith("[HA Control]"):
            continue

        if line.startswith("- "):
            continue

        if line.startswith("Matching candidates"):
            continue

        if line.startswith("Backend endpoint:"):
            continue

        if line.startswith("Payload"):
            continue

        if line.startswith("Backend response:"):
            continue

        lines.append(line)

    compact = " ".join(lines)
    compact = re.sub(r"\s+", " ", compact).strip()

    if not compact:
        return "Home Assistant control completed, but I could not extract a clean summary."

    if len(compact) > 220:
        compact = compact[:220].rsplit(" ", 1)[0] + "."

    return compact


def run_home_assistant_control_mode(config: dict[str, Any], command_text: str) -> tuple[int, str, str]:
    project_root = Path(config.get("project_root", str(PROJECT_ROOT)))
    python_command = config.get("python_command", "python")

    ha_control_path = project_root / "voice" / "home_assistant_control.py"

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        [python_command, str(ha_control_path), "--text", command_text, "--yes"],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
        env=env,
    )

    combined_output = ""

    if result.stdout:
        combined_output += result.stdout

    if result.stderr:
        combined_output += "\n[stderr]\n" + result.stderr

    summary = extract_summary_from_home_assistant_control_output(combined_output)

    return result.returncode, combined_output.strip(), summary

def is_home_assistant_read_phrase(text: str) -> bool:
    normalized = normalize_text(text)

    control_indicators = [
        "turn on",
        "turn off",
        "switch on",
        "switch off",
        "toggle",
        "set temperature",
        "change temperature",
        "unlock",
        "lock",
        "open",
        "close",
        "restart",
        "reboot",
        "delete",
        "remove",
        "modify",
        "edit",
    ]

    if any(item in normalized for item in control_indicators):
        return False

    read_indicators = [
        "home assistant",
        "home devices",
        "smart home",
        "home status",
        "devices",
        "device",
        "entities",
        "entity",
        "unavailable devices",
        "unavailable",
        "offline",
        "camera",
        "cameras",
        "cctv",
        "switch",
        "switches",
        "sensor",
        "sensors",
        "binary sensor",
        "binary sensors",
        "show camera",
        "show cameras",
        "show switch",
        "show switches",
        "show sensor",
        "show sensors",
        "is camera working",
        "is cctv working",
        "find device",
        "search device",
    ]

    return any(item in normalized for item in read_indicators)

def extract_summary_from_home_assistant_output(output: str) -> str:
    lines = []

    for raw_line in output.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        if line.startswith("[HA Voice]"):
            continue

        if line.startswith("- "):
            continue

        if line.lower().startswith("domain breakdown"):
            continue

        if line.lower().startswith("top domains"):
            continue

        if line.lower().startswith("recent home assistant entities"):
            continue

        if line.startswith("---"):
            continue

        lines.append(line)

    compact = " ".join(lines)
    compact = re.sub(r"\s+", " ", compact).strip()

    if not compact:
        return "Home Assistant read-only command completed, but I could not extract a clean summary."

    if len(compact) > 360:
        compact = compact[:360].rsplit(" ", 1)[0] + "."

    return compact


def run_home_assistant_text_mode(config: dict[str, Any], command_text: str) -> tuple[int, str, str]:
    project_root = Path(config.get("project_root", str(PROJECT_ROOT)))
    python_command = config.get("python_command", "python")

    ha_cli_path = project_root / "voice" / "home_assistant_read.py"

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        [python_command, str(ha_cli_path), "--text", command_text],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        env=env,
    )

    combined_output = ""

    if result.stdout:
        combined_output += result.stdout

    if result.stderr:
        combined_output += "\n[stderr]\n" + result.stderr

    summary = extract_summary_from_home_assistant_output(combined_output)

    return result.returncode, combined_output.strip(), summary

def run_voice_cli_text_mode(config: dict[str, Any], command_text: str) -> tuple[int, str, str]:
    project_root = Path(config.get("project_root", str(PROJECT_ROOT)))
    python_command = config.get("python_command", "python")

    voice_cli_path = project_root / "voice" / "voice_cli.py"

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        [python_command, str(voice_cli_path), "--text", command_text],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        env=env,
    )

    combined_output = ""

    if result.stdout:
        combined_output += result.stdout

    if result.stderr:
        combined_output += "\n[stderr]\n" + result.stderr

    summary = extract_summary_from_voice_cli_output(combined_output)

    return result.returncode, combined_output.strip(), summary



# ============================================================
# V2C-A ROUTING OVERRIDES
# These definitions intentionally override earlier routing helpers.
# Purpose:
# - Route Home Assistant control phrases to home_assistant_control.py
# - Route Home Assistant read-only phrases to home_assistant_read.py
# - Route normal Vetri commands to voice_cli.py
# ============================================================

def is_home_assistant_control_phrase(text: str) -> bool:
    normalized = normalize_text(text)

    control_indicators = [
        "turn on",
        "turn off",
        "switch on",
        "switch off",
        "start",
        "stop",
    ]

    high_risk_indicators = [
        "unlock",
        "lock",
        "open",
        "close",
        "restart",
        "reboot",
        "shutdown",
        "delete",
        "remove",
        "set temperature",
        "change temperature",
    ]

    return any(item in normalized for item in control_indicators + high_risk_indicators)


def is_home_assistant_read_phrase(text: str) -> bool:
    normalized = normalize_text(text)

    # If it is a control phrase, do not treat it as read-only.
    if is_home_assistant_control_phrase(text):
        return False

    read_indicators = [
        "home assistant",
        "home devices",
        "smart home",
        "home status",
        "devices",
        "device",
        "entities",
        "entity",
        "unavailable",
        "offline",
        "camera",
        "cameras",
        "cctv",
        "switch",
        "switches",
        "sensor",
        "sensors",
        "binary sensor",
        "binary sensors",
        "show camera",
        "show cameras",
        "show switch",
        "show switches",
        "show sensor",
        "show sensors",
        "is camera working",
        "is cctv working",
        "find device",
        "search device",
    ]

    return any(item in normalized for item in read_indicators)


def extract_summary_from_home_assistant_control_output(output: str) -> str:
    action_match = re.search(r"Action:\s*(turn_on|turn_off)", output, re.IGNORECASE)
    entity_match = re.search(r"Entity:\s*(.+)", output, re.IGNORECASE)
    entity_id_match = re.search(r"Entity ID:\s*(.+)", output, re.IGNORECASE)
    status_match = re.search(r"Status code:\s*(\d+)", output, re.IGNORECASE)
    dry_run_match = re.search(r"Dry run successful\..+?No device was changed\.", output, re.IGNORECASE)

    action = action_match.group(1).strip() if action_match else ""
    entity = entity_match.group(1).strip() if entity_match else "the selected device"
    entity_id = entity_id_match.group(1).strip() if entity_id_match else ""
    status_code = status_match.group(1).strip() if status_match else ""

    friendly_action = {
        "turn_on": "turned on",
        "turn_off": "turned off",
    }.get(action, action)

    if dry_run_match:
        return f"Dry run successful. I would have {friendly_action} {entity}, but no device was changed."

    if "BACKEND LIVE REQUEST SENT" in output and status_code == "200":
        return f"Done. I {friendly_action} {entity} through the Vetri backend."

    if "BACKEND LIVE FAILED SAFELY" in output:
        return f"I could not control {entity}. The backend live request failed safely, and no direct Home Assistant call was made from Windows."

    if "LIVE POLICY BLOCK" in output:
        return f"I blocked this Home Assistant action because the matched entity is not enabled for live voice control."

    if "POLICY BLOCK" in output:
        return f"I blocked this Home Assistant action by policy."

    if "AMBIGUOUS" in output:
        return "I found more than one matching Home Assistant device. Please use a more specific name."

    if "NO MATCH" in output:
        return "I could not find a matching Home Assistant device for that command."

    if "BLOCKED" in output:
        return "I blocked that Home Assistant action because it is not allowed from voice control."

    lines = []

    for raw_line in output.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        if line.startswith("[HA Control]"):
            continue

        if line.startswith("- "):
            continue

        if line.startswith("Matching candidates"):
            continue

        if line.startswith("Backend endpoint:"):
            continue

        if line.startswith("Payload"):
            continue

        if line.startswith("Backend response:"):
            continue

        lines.append(line)

    compact = " ".join(lines)
    compact = re.sub(r"\s+", " ", compact).strip()

    if not compact:
        return "Home Assistant control completed, but I could not extract a clean summary."

    if len(compact) > 220:
        compact = compact[:220].rsplit(" ", 1)[0] + "."

    return compact


def extract_summary_from_home_assistant_output(output: str) -> str:
    lines = []

    for raw_line in output.splitlines():
        line = raw_line.strip()

        if not line:
            continue

        if line.startswith("[HA Voice]"):
            continue

        if line.startswith("- "):
            continue

        if line.lower().startswith("domain breakdown"):
            continue

        if line.lower().startswith("top domains"):
            continue

        if line.lower().startswith("home assistant entities"):
            continue

        if line.lower().startswith("recent home assistant entities"):
            continue

        if line.startswith("---"):
            continue

        lines.append(line)

    compact = " ".join(lines)
    compact = re.sub(r"\s+", " ", compact).strip()

    if not compact:
        return "Home Assistant read-only command completed, but I could not extract a clean summary."

    if len(compact) > 360:
        compact = compact[:360].rsplit(" ", 1)[0] + "."

    return compact


def run_home_assistant_control_mode(config: dict[str, Any], command_text: str) -> tuple[int, str, str]:
    project_root = Path(config.get("project_root", str(PROJECT_ROOT)))
    python_command = config.get("python_command", "python")

    ha_control_path = project_root / "voice" / "home_assistant_control.py"

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        [python_command, str(ha_control_path), "--text", command_text, "--yes"],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
        env=env,
    )

    combined_output = ""

    if result.stdout:
        combined_output += result.stdout

    if result.stderr:
        combined_output += "\n[stderr]\n" + result.stderr

    summary = extract_summary_from_home_assistant_control_output(combined_output)

    return result.returncode, combined_output.strip(), summary


def run_home_assistant_text_mode(config: dict[str, Any], command_text: str) -> tuple[int, str, str]:
    project_root = Path(config.get("project_root", str(PROJECT_ROOT)))
    python_command = config.get("python_command", "python")

    ha_cli_path = project_root / "voice" / "home_assistant_read.py"

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        [python_command, str(ha_cli_path), "--text", command_text],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=60,
        env=env,
    )

    combined_output = ""

    if result.stdout:
        combined_output += result.stdout

    if result.stderr:
        combined_output += "\n[stderr]\n" + result.stderr

    summary = extract_summary_from_home_assistant_output(combined_output)

    return result.returncode, combined_output.strip(), summary


def run_voice_cli_text_mode(config: dict[str, Any], command_text: str) -> tuple[int, str, str]:
    """
    V2C-A router.

    Even if an earlier code path falls back to this function, this router
    catches Home Assistant control/read-only phrases first.
    """
    if is_home_assistant_control_phrase(command_text):
        return_code, output, summary = run_home_assistant_control_mode(
            config=config,
            command_text=command_text,
        )

        decorated_output = (
            "========== home_assistant_control.py --text output ==========\n"
            f"{output if output else '[No output]'}\n"
            "============================================================"
        )

        return return_code, decorated_output, summary

    if is_home_assistant_read_phrase(command_text):
        return_code, output, summary = run_home_assistant_text_mode(
            config=config,
            command_text=command_text,
        )

        decorated_output = (
            "========== home_assistant_read.py --text output ==========\n"
            f"{output if output else '[No output]'}\n"
            "========================================================="
        )

        return return_code, decorated_output, summary

    project_root = Path(config.get("project_root", str(PROJECT_ROOT)))
    python_command = config.get("python_command", "python")

    voice_cli_path = project_root / "voice" / "voice_cli.py"

    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    result = subprocess.run(
        [python_command, str(voice_cli_path), "--text", command_text],
        cwd=str(project_root),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        env=env,
    )

    combined_output = ""

    if result.stdout:
        combined_output += result.stdout

    if result.stderr:
        combined_output += "\n[stderr]\n" + result.stderr

    summary = extract_summary_from_voice_cli_output(combined_output)

    return result.returncode, combined_output.strip(), summary


# ============================================================
# V1A.2-B SMART COMMAND GUARD
# Prevents silence/noise/STT hallucination from becoming actions.
# ============================================================

def command_audio_is_too_quiet(rms: float, config: dict[str, Any]) -> bool:
    threshold = float(config.get("command_min_rms", 0.0065))
    return rms < threshold


def wake_audio_is_too_quiet(rms: float, config: dict[str, Any]) -> bool:
    threshold = float(config.get("wake_min_rms", 0.0045))
    return rms < threshold


def transcript_is_mostly_non_latin(text: str) -> bool:
    clean = text.strip()

    if not clean:
        return False

    latin_count = sum(1 for ch in clean if ("a" <= ch.lower() <= "z"))
    alpha_count = sum(1 for ch in clean if ch.isalpha())

    if alpha_count == 0:
        return False

    return latin_count / alpha_count < 0.45


def command_transcript_is_actionable(text: str) -> tuple[bool, str]:
    normalized = normalize_text(text)

    if not normalized:
        return False, "empty transcript"

    if len(normalized) < 4:
        return False, "too short"

    if transcript_is_mostly_non_latin(text):
        return False, "mostly non-Latin transcript"

    # Do not execute filler/hallucinated endings.
    ignored_exact = {
        "thank you",
        "thanks",
        "okay",
        "ok",
        "hello",
        "hey",
        "yes",
        "no",
        "bye",
        "goodbye",
    }

    if normalized in ignored_exact:
        return False, "filler phrase"

    # A command must contain a real Vetri/Home Assistant action or query cue.
    allowed_cues = [
        "turn on",
        "turn off",
        "switch on",
        "switch off",
        "diagnose",
        "validate",
        "home assistant",
        "home status",
        "show",
        "list",
        "how many",
        "camera",
        "cameras",
        "sensor",
        "sensors",
        "switch",
        "switches",
        "device",
        "devices",
        "fan",
        "light",
        "lights",
        "strip light",
        "backend",
        "frontend",
        "network",
        "storage",
        "backup",
        "immich",
        "repeat",
        "mute",
        "unmute",
        "logs",
    ]

    if not any(cue in normalized for cue in allowed_cues):
        return False, "no approved command cue"

    return True, "accepted"


def safe_command_prompt(config: dict[str, Any]) -> str:
    return config.get(
        "command_prompt",
        (
            "Transcribe exactly what the user says after the wake phrase. "
            "Do not invent a command if the audio is silent, unclear, or background noise. "
            "If nothing clear is spoken, return an empty transcript."
        ),
    )

def run_once(client: OpenAI, config: dict[str, Any]) -> None:
    sample_rate = int(config.get("sample_rate", 16000))

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        wake_wav = tmp / "wake.wav"
        command_wav = tmp / "command.wav"

        print()
        print("[Vetri Wake] Say the wake phrase now: Hey Vetri")

        record_audio(
            output_wav=wake_wav,
            seconds=float(config.get("wake_record_seconds", 2.5)),
            sample_rate=sample_rate,
            label="wake phrase",
        )

        wake_transcript = transcribe_audio(
            client=client,
            wav_path=wake_wav,
            model=config.get("speech_to_text_model", "gpt-4o-mini-transcribe"),
            prompt=config.get("wake_prompt", "The user may say Hey Vetri."),
        )

        print(f"[Vetri Wake] Heard wake chunk: {wake_transcript}")

        if not has_wake_phrase(wake_transcript, config.get("wake_phrases", [])):
            print("[Vetri Wake] Wake phrase not detected.")
            return

        print("[Vetri Wake] Wake phrase detected.")
        play_beep()

        if config.get("speak_wake_ack", True):
            speak_text(
                client=client,
                text=config.get("wake_ack_text", "Yes, I am listening."),
                config=config,
            )

        print("[Vetri Wake] Speak your Vetri command now.")

        command_rms = record_audio(
            output_wav=command_wav,
            seconds=float(config.get("command_record_seconds", 5)),
            sample_rate=sample_rate,
            label="command",
        )

        if command_audio_is_too_quiet(command_rms, config):
            message = "I did not hear a clear command after the wake phrase."
            print(f"[Vetri Wake] {message}")
            return

        command_transcript = transcribe_audio(
            client=client,
            wav_path=command_wav,
            model=config.get("speech_to_text_model", "gpt-4o-mini-transcribe"),
            prompt=safe_command_prompt(config),
        )

        print(f"[Vetri Wake] Heard command: {command_transcript}")

        actionable, reason = command_transcript_is_actionable(command_transcript)

        if not actionable:
            message = f"I ignored that input because it was not a clear approved command: {reason}."
            print(f"[Vetri Wake] {message}")
            return

        if is_home_assistant_read_phrase(command_transcript):
            return_code, output, summary = run_home_assistant_text_mode(
                config=config,
                command_text=command_transcript,
            )

            print()
            print("========== home_assistant_read.py --text output ==========")
            print(output if output else "[No output]")
            print("=========================================================")
            print(f"[Vetri Wake] Home Assistant Summary: {summary}")
        else:
            if is_home_assistant_read_phrase(command_transcript):
                return_code, output, summary = run_home_assistant_text_mode(
                    config=config,
                    command_text=command_transcript,
                )

                print()
                print("========== home_assistant_read.py --text output ==========")
                print(output if output else "[No output]")
                print("=========================================================")
                print(f"[Vetri Wake] Home Assistant Summary: {summary}")
            else:
                return_code, output, summary = run_voice_cli_text_mode(
                    config=config,
                    command_text=command_transcript,
                )

                print()
                print("========== voice_cli.py --text output ==========")
                print(output if output else "[No output]")
                print("===============================================")
                print(f"[Vetri Wake] Summary: {summary}")

        speak_text(client=client, text=summary, config=config)

        if return_code != 0:
            print(f"[Vetri Wake] voice_cli.py returned non-zero code: {return_code}")


def continuous_loop(client: OpenAI, config: dict[str, Any]) -> None:
    sample_rate = int(config.get("sample_rate", 16000))
    empty_count = 0

    print()
    print("========================================")
    print(" Vetri Wake Listener V1A")
    print("========================================")
    print("Say: Hey Vetri")
    print("Then speak a safe Vetri command.")
    print("Ctrl+C to stop.")
    print("Safety: wake listener routes only through voice_cli.py --text.")
    print("No Home Assistant control. No Spotify. No write actions.")
    print("========================================")

    while True:
        with tempfile.TemporaryDirectory() as tmpdir:
            wake_wav = Path(tmpdir) / "wake_loop.wav"

            record_audio(
                output_wav=wake_wav,
                seconds=float(config.get("wake_record_seconds", 2.5)),
                sample_rate=sample_rate,
                label="wake-listen chunk",
            )

            try:
                wake_transcript = transcribe_audio(
                    client=client,
                    wav_path=wake_wav,
                    model=config.get("speech_to_text_model", "gpt-4o-mini-transcribe"),
                    prompt=config.get("wake_prompt", "The user may say Hey Vetri."),
                )
            except Exception as exc:
                print(f"[Vetri Wake] STT error during wake listening: {exc}")
                time.sleep(2)
                continue

        if wake_transcript.strip():
            print(f"[Vetri Wake] Heard: {wake_transcript}")
        else:
            empty_count += 1

            hint_limit = int(config.get("max_empty_wake_transcripts_before_hint", 8))

            if empty_count >= hint_limit:
                print("[Vetri Wake] Still listening for: Hey Vetri")
                empty_count = 0

        if has_wake_phrase(wake_transcript, config.get("wake_phrases", [])):
            print("[Vetri Wake] Wake phrase detected.")
            play_beep()

            if config.get("speak_wake_ack", True):
                speak_text(
                    client=client,
                    text=config.get("wake_ack_text", "Yes, I am listening."),
                    config=config,
                )

            with tempfile.TemporaryDirectory() as tmpdir:
                command_wav = Path(tmpdir) / "command_loop.wav"

                print("[Vetri Wake] Speak your Vetri command now.")

                command_rms = record_audio(
                    output_wav=command_wav,
                    seconds=float(config.get("command_record_seconds", 5)),
                    sample_rate=sample_rate,
                    label="command",
                )

                if command_audio_is_too_quiet(command_rms, config):
                    message = "I did not hear a clear command after the wake phrase."
                    print(f"[Vetri Wake] {message}")
                    time.sleep(float(config.get("wake_cooldown_seconds", 1.5)))
                    continue

                try:
                    command_transcript = transcribe_audio(
                        client=client,
                        wav_path=command_wav,
                        model=config.get("speech_to_text_model", "gpt-4o-mini-transcribe"),
                        prompt=safe_command_prompt(config),
                    )
                except Exception as exc:
                    message = f"I had trouble transcribing the command: {exc}"
                    print(f"[Vetri Wake] {message}")
                    speak_text(client=client, text="I had trouble transcribing the command.", config=config)
                    time.sleep(float(config.get("wake_cooldown_seconds", 1.5)))
                    continue

            print(f"[Vetri Wake] Heard command: {command_transcript}")

            actionable, reason = command_transcript_is_actionable(command_transcript)

            if not actionable:
                message = f"I ignored that input because it was not a clear approved command: {reason}."
                print(f"[Vetri Wake] {message}")
                time.sleep(float(config.get("wake_cooldown_seconds", 1.5)))
                continue

            if is_home_assistant_read_phrase(command_transcript):
                return_code, output, summary = run_home_assistant_text_mode(
                    config=config,
                    command_text=command_transcript,
                )

                print()
                print("========== home_assistant_read.py --text output ==========")
                print(output if output else "[No output]")
                print("=========================================================")
                print(f"[Vetri Wake] Home Assistant Summary: {summary}")
            else:
                return_code, output, summary = run_voice_cli_text_mode(
                    config=config,
                    command_text=command_transcript,
                )

                print()
                print("========== voice_cli.py --text output ==========")
                print(output if output else "[No output]")
                print("===============================================")
                print(f"[Vetri Wake] Summary: {summary}")

            speak_text(client=client, text=summary, config=config)

            if return_code != 0:
                print(f"[Vetri Wake] voice_cli.py returned non-zero code: {return_code}")

            time.sleep(float(config.get("wake_cooldown_seconds", 1.5)))


def test_detection(config: dict[str, Any], text: str) -> None:
    print()
    print("========================================")
    print(" Vetri Wake Listener V1A - Detection Test")
    print("========================================")
    print(f"Input:      {text}")
    print(f"Normalized: {normalize_text(text)}")
    print(f"Detected:   {has_wake_phrase(text, config.get('wake_phrases', []))}")
    print("========================================")


def main() -> None:
    parser = argparse.ArgumentParser(description="Vetri Wake Listener V1A")
    parser.add_argument(
        "--once",
        action="store_true",
        help="Run one wake phrase + command attempt and exit.",
    )
    parser.add_argument(
        "--test-detect",
        type=str,
        default=None,
        help="Test wake phrase detection on typed text.",
    )

    args = parser.parse_args()

    config = load_config()
    project_root = Path(config.get("project_root", str(PROJECT_ROOT)))

    if args.test_detect is not None:
        test_detection(config, args.test_detect)
        return

    load_environment(project_root)

    if not os.getenv("OPENAI_API_KEY"):
        raise EnvironmentError(
            "OPENAI_API_KEY not found. Add it to Z:\\HomeLLM\\.env."
        )

    client = OpenAI()

    if args.once:
        run_once(client, config)
        return

    continuous_loop(client, config)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[Vetri Wake] Stopped by user.")
    except Exception as exc:
        print(f"\n[Vetri Wake] ERROR: {exc}")
        sys.exit(1)
