from __future__ import annotations

import argparse
import json
import os
import queue
import re
import subprocess
import sys
import tempfile
import time
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import sounddevice as sd
from dotenv import load_dotenv
from openai import OpenAI


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VOICE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = VOICE_DIR / "terminal_openwakeword_config.json"


try:
    from vetri_tts import speak_command_result
except Exception:
    speak_command_result = None


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_config() -> dict[str, Any]:
    default = {
        "wake_model_name": "hey_jarvis",
        "wake_threshold": 0.55,
        "wake_cooldown_seconds": 1.2,
        "sample_rate": 16000,
        "frame_ms": 80,
        "command_record_seconds": 5,
        "command_min_rms": 0.0065,
        "speech_to_text_model": "gpt-4o-mini-transcribe",
        "command_prompt": (
            "Transcribe exactly what the user says after the wake word. "
            "Do not invent a command if the audio is silent, unclear, or background noise. "
            "If nothing clear is spoken, return an empty transcript."
        ),
        "log_file": str(VOICE_DIR / "logs" / "terminal_openwakeword.log"),
        "print_wake_scores": False,
        "debug_every_n_frames": 0,
        "post_command_wake_lockout_seconds": 4.0,
        "tts_enabled": True,
        "tts_rate": 0,
        "tts_volume": 90,
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


def log(config: dict[str, Any], message: str) -> None:
    print(message, flush=True)

    try:
        log_path = Path(str(config.get("log_file")))
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(f"{now()} | {message}\n")
    except Exception:
        pass


def beep() -> None:
    if sys.platform.startswith("win"):
        try:
            import winsound
            winsound.Beep(920, 110)
            winsound.Beep(1180, 130)
            return
        except Exception:
            pass

    print("\a", end="", flush=True)


def maybe_speak_summary(config: dict[str, Any], summary: str) -> None:
    """
    Speak command result locally on Windows.

    This is intentionally called only after a routed command completes.
    It does not speak during idle, wake-only mode, timeout, or ignored commands.
    """

    if speak_command_result is None:
        log(config, "[Vetri TTS] TTS module unavailable. Skipping speech.")
        return

    enabled = bool(config.get("tts_enabled", True))

    if not enabled:
        return

    try:
        rate = int(config.get("tts_rate", 0))
        volume = int(config.get("tts_volume", 90))

        ok = speak_command_result(
            summary=summary,
            enabled=enabled,
            rate=rate,
            volume=volume,
        )

        if ok:
            log(config, "[Vetri TTS] Spoken response queued.")
        else:
            log(config, "[Vetri TTS] Speech skipped.")

    except Exception as exc:
        log(config, f"[Vetri TTS] Speech failed safely: {exc}")


def normalize_text(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def command_transcript_is_actionable(text: str) -> tuple[bool, str]:
    normalized = normalize_text(text)

    if not normalized:
        return False, "empty transcript"

    if len(normalized) < 4:
        return False, "too short"

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

    cues = [
        # Home Assistant / system control
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
        "latest export",
        "mac export",
        "monitoring",
        "memory",
        "remember",
        "project",
        "friend",
        "talk to me",
        "how am i doing",
        "plan how",

        # Spotify / media control
        "spotify",
        "music",
        "song",
        "songs",
        "track",
        "tracks",
        "play",
        "pause",
        "resume",
        "continue",
        "next song",
        "next track",
        "previous song",
        "previous track",
        "skip song",
        "skip track",
        "what song",
        "currently playing",
        "volume up",
        "volume down",
        "increase volume",
        "decrease volume",
        "lower volume",
        "set volume",
    ]

    if not any(cue in normalized for cue in cues):
        return False, "no approved command cue"

    return True, "accepted"


def write_wav(path: Path, pcm: np.ndarray, sample_rate: int) -> float:
    pcm = pcm.astype(np.int16)

    if pcm.size == 0:
        rms = 0.0
    else:
        rms = float(np.sqrt(np.mean(np.square(pcm.astype(np.float32) / 32768.0))))

    with wave.open(str(path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm.tobytes())

    return rms


def transcribe_command(client: OpenAI, wav_path: Path, config: dict[str, Any]) -> str:
    with wav_path.open("rb") as audio_file:
        transcription = client.audio.transcriptions.create(
            model=config.get("speech_to_text_model", "gpt-4o-mini-transcribe"),
            file=audio_file,
            response_format="text",
            prompt=config.get("command_prompt"),
        )

    if isinstance(transcription, str):
        return transcription.strip()

    return str(transcription).strip()


def extract_summary(output: str) -> str:
    patterns = [
        r"Spotify summary:\s*(.+)",
        r"Control summary:\s*(.+)",
        r"\[Vetri Voice\] Text-mode spoken summary:\s*(.+)",
        r"\[BLOCKED\]\s*(.+)",
        r"\[POLICY BLOCK\]\s*(.+)",
        r"\[NO SAFE MATCH\].*?\n(.+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, output, re.IGNORECASE | re.DOTALL)

        if match:
            summary = match.group(1).strip().splitlines()[0].strip()
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

        if lower.startswith("[ha control]"):
            continue

        if lower.startswith("backend response:"):
            continue

        if lower.startswith("backend endpoint:"):
            continue

        if lower.startswith("payload"):
            continue

        if lower.startswith("input:"):
            continue

        lines.append(line)

    compact = " ".join(lines)
    compact = re.sub(r"\s+", " ", compact).strip()

    if not compact:
        return "Command completed, but no clean summary was found."

    if len(compact) > 260:
        compact = compact[:260].rsplit(" ", 1)[0] + "."

    return compact


def looks_like_spotify_command(normalized: str) -> bool:
    """
    Decides whether the text should route to Spotify control.

    This is intentionally conservative where possible, but allows natural commands like:
    - pause music
    - resume music
    - next song
    - what song is playing
    - play Blinding Lights
    """

    exact_commands = {
        "spotify status",
        "what song is playing",
        "what is playing",
        "current song",
        "currently playing",
        "pause spotify",
        "spotify pause",
        "pause music",
        "pause song",
        "stop music",
        "stop spotify",
        "resume spotify",
        "spotify resume",
        "play music",
        "resume music",
        "continue music",
        "play spotify",
        "next song",
        "next track",
        "skip song",
        "skip track",
        "spotify next",
        "next spotify",
        "previous song",
        "previous track",
        "go back song",
        "spotify previous",
        "previous spotify",
    }

    if normalized in exact_commands:
        return True

    spotify_cues = [
        "spotify",
        "music",
        "song",
        "track",
        "currently playing",
        "what song",
        "volume up",
        "volume down",
        "increase volume",
        "decrease volume",
        "lower volume",
        "set volume",
    ]

    if any(cue in normalized for cue in spotify_cues):
        return True

    # Natural search command:
    # "play blinding lights", "play arijit singh", etc.
    # Do not treat "play" alone as enough.
    if normalized.startswith("play ") and len(normalized.split()) >= 2:
        blocked_home_words = {
            "light",
            "lights",
            "fan",
            "switch",
            "device",
            "devices",
            "camera",
            "cameras",
            "sensor",
            "sensors",
            "backend",
            "frontend",
            "backup",
            "storage",
            "network",
            "immich",
        }

        words = set(normalized.split())

        if not words.intersection(blocked_home_words):
            return True

    return False


def run_router(command_text: str) -> tuple[int, str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"

    normalized = normalize_text(command_text)

    control_cues = [
        "turn on",
        "turn off",
        "switch on",
        "switch off",
        "start",
        "stop",
    ]

    read_cues = [
        "home assistant",
        "home status",
        "show camera",
        "show cameras",
        "show unavailable",
        "how many home",
        "list home",
        "show sensors",
        "show switches",
    ]

    if looks_like_spotify_command(normalized):
        script = VOICE_DIR / "spotify_control.py"
        args = [sys.executable, str(script), "--text", command_text]
        route = "spotify_control"
    elif any(cue in normalized for cue in control_cues):
        script = VOICE_DIR / "home_assistant_control.py"
        args = [sys.executable, str(script), "--text", command_text, "--yes"]
        route = "home_assistant_control"
    elif any(cue in normalized for cue in read_cues):
        script = VOICE_DIR / "home_assistant_read.py"
        args = [sys.executable, str(script), "--text", command_text]
        route = "home_assistant_read"
    else:
        features_path = PROJECT_ROOT / "config" / "features.json"
        voice_ai_enabled = False

        try:
            if features_path.exists():
                with features_path.open("r", encoding="utf-8") as feature_file:
                    voice_ai_enabled = bool(json.load(feature_file).get("voice_ai_integration_v4_enabled", False))
        except Exception:
            voice_ai_enabled = False

        if voice_ai_enabled:
            try:
                from vetri_ai.voice.voice_ai_bridge import handle_voice_text

                bridge_result = handle_voice_text(command_text)
                route = "vetri_ai_bridge"
                response_text = str(bridge_result.get("response_text") or "The AI brain handled the request.")
                output = (
                    f"[Router] Route: {route}\n"
                    f"Safety: {bridge_result.get('safety_status')}\n"
                    f"AI route: {bridge_result.get('route')}\n"
                    f"{response_text}"
                )
                return 0, output.strip(), extract_summary(output)
            except Exception as exc:
                route = "vetri_ai_bridge"
                output = (
                    f"[Router] Route: {route}\n"
                    f"[Vetri AI] The AI brain had an issue, but the voice system is still running.\n"
                    f"[Vetri AI error handled safely: {exc}]"
                )
                return 0, output.strip(), "The AI brain had an issue, but the voice system is still running."

        script = VOICE_DIR / "voice_cli.py"
        args = [sys.executable, str(script), "--text", command_text]
        route = "vetri_voice_cli"

    result = subprocess.run(
        args,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
        env=env,
    )

    output = f"[Router] Route: {route}\n"

    if result.stdout:
        output += result.stdout

    if result.stderr:
        output += "\n[stderr]\n" + result.stderr

    summary = extract_summary(output)

    return result.returncode, output.strip(), summary


def list_devices() -> None:
    print("Available input devices:")
    devices = sd.query_devices()

    for idx, device in enumerate(devices):
        if int(device.get("max_input_channels", 0)) > 0:
            print(f"[{idx}] {device.get('name')} | inputs={device.get('max_input_channels')} | default_sr={device.get('default_samplerate')}")


def load_openwakeword_model(config: dict[str, Any]):
    import openwakeword
    from openwakeword.model import Model

    print("[Vetri] Downloading/checking openWakeWord models if needed...", flush=True)
    openwakeword.utils.download_models()

    print("[Vetri] Loading openWakeWord model...", flush=True)
    model = Model()

    return model


def get_wake_score(prediction: dict[str, float], configured_model_name: str) -> tuple[str, float]:
    if not prediction:
        return "", 0.0

    if configured_model_name in prediction:
        return configured_model_name, float(prediction[configured_model_name])

    # Try flexible matching because model keys can differ slightly by version.
    configured_norm = configured_model_name.replace("_", " ").replace("-", " ").lower()

    for key, value in prediction.items():
        key_norm = str(key).replace("_", " ").replace("-", " ").lower()

        if configured_norm == key_norm:
            return str(key), float(value)

    # Fallback: use highest model score.
    best_key = max(prediction, key=lambda item: float(prediction[item]))
    return str(best_key), float(prediction[best_key])


def drain_audio_queue(audio_queue: queue.Queue[np.ndarray], max_items: int = 200) -> int:
    drained = 0

    while drained < max_items:
        try:
            audio_queue.get_nowait()
            drained += 1
        except queue.Empty:
            break

    return drained


def reset_wake_model_if_supported(model: Any) -> None:
    reset_fn = getattr(model, "reset", None)

    if callable(reset_fn):
        try:
            reset_fn()
        except Exception:
            pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Vetri Terminal openWakeWord Layer V2C")
    parser.add_argument("--list-devices", action="store_true")
    parser.add_argument("--device-index", type=int, default=None)
    parser.add_argument("--threshold", type=float, default=None)
    args = parser.parse_args()

    if args.list_devices:
        list_devices()
        return

    load_environment()
    config = load_config()

    if args.threshold is not None:
        config["wake_threshold"] = args.threshold

    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY missing in Z:\\HomeLLM\\.env")

    client = OpenAI()

    sample_rate = int(config.get("sample_rate", 16000))
    frame_ms = int(config.get("frame_ms", 80))
    block_size = int(sample_rate * frame_ms / 1000)
    wake_model_name = str(config.get("wake_model_name", "hey_jarvis"))
    wake_threshold = float(config.get("wake_threshold", 0.55))

    model = load_openwakeword_model(config)

    audio_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=200)

    def callback(indata, frames, time_info, status):
        if status:
            return

        try:
            frame = indata[:, 0].copy().astype(np.int16)
            audio_queue.put_nowait(frame)
        except queue.Full:
            pass

    log(config, "========================================")
    log(config, " Vetri Terminal openWakeWord V2C")
    log(config, "========================================")
    log(config, f"Wake model target: {wake_model_name}")
    log(config, f"Wake threshold: {wake_threshold}")
    log(config, f"Sample rate: {sample_rate}")
    log(config, f"Block size: {block_size} samples")
    log(config, f"TTS enabled: {bool(config.get('tts_enabled', True))}")
    log(config, "Spotify route: enabled")
    log(config, "State: WAKE_ONLY")
    log(config, "Temporary wake phrase for now: hey jarvis")
    log(config, "After wake, speak command within 5 seconds.")
    log(config, "Press Ctrl+C to stop.")
    log(config, "========================================")

    frame_count = 0
    last_detection_at = 0.0
    ignore_wake_until = 0.0

    try:
        with sd.InputStream(
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
            blocksize=block_size,
            device=args.device_index,
            callback=callback,
        ):
            while True:
                frame = audio_queue.get()
                frame_count += 1

                prediction = model.predict(frame)
                matched_model, score = get_wake_score(prediction, wake_model_name)

                if bool(config.get("print_wake_scores", False)):
                    if score > 0.10:
                        log(config, f"[WakeScore] {matched_model}: {score:.3f}")

                debug_every = int(config.get("debug_every_n_frames", 0))

                if debug_every > 0 and frame_count % debug_every == 0:
                    log(config, f"[Debug] Still wake-only. Current best: {matched_model}={score:.3f}")

                now_ts = time.time()

                if time.time() < ignore_wake_until:
                    continue

                if score < wake_threshold:
                    continue

                if now_ts - last_detection_at < float(config.get("wake_cooldown_seconds", 1.2)):
                    continue

                last_detection_at = now_ts

                log(config, f"[Vetri] Wake detected by {matched_model} with score {score:.3f}")
                reset_wake_model_if_supported(model)
                drained = drain_audio_queue(audio_queue, max_items=80)

                if drained:
                    log(config, f"[Vetri] Drained {drained} buffered audio frame(s) after wake detection.")

                beep()

                command_frames: list[np.ndarray] = []
                target_frames = int(float(config.get("command_record_seconds", 5)) * sample_rate / block_size)

                log(config, f"[Vetri] Listening for command for {config.get('command_record_seconds', 5)} seconds...")

                for _ in range(target_frames):
                    command_frames.append(audio_queue.get())

                command_pcm = np.concatenate(command_frames)

                with tempfile.TemporaryDirectory() as tmpdir:
                    wav_path = Path(tmpdir) / "command.wav"
                    rms = write_wav(wav_path, command_pcm, sample_rate)

                    log(config, f"[Vetri] Command audio RMS: {rms:.6f}")

                    if rms < float(config.get("command_min_rms", 0.0065)):
                        log(config, "[Vetri] No clear command heard. Returning to wake-only mode.")
                        reset_wake_model_if_supported(model)
                        drained = drain_audio_queue(audio_queue, max_items=200)

                        if drained:
                            log(config, f"[Vetri] Drained {drained} buffered audio frame(s) after quiet command window.")

                        ignore_wake_until = time.time() + float(config.get("post_command_wake_lockout_seconds", 4.0))
                        log(config, "State: WAKE_ONLY")
                        continue

                    transcript = transcribe_command(client, wav_path, config)
                    log(config, f"[Vetri] Heard command: {transcript}")

                    actionable, reason = command_transcript_is_actionable(transcript)

                    if not actionable:
                        log(config, f"[Vetri] Ignored command: {reason}. Returning to wake-only mode.")
                        reset_wake_model_if_supported(model)
                        drained = drain_audio_queue(audio_queue, max_items=200)

                        if drained:
                            log(config, f"[Vetri] Drained {drained} buffered audio frame(s) after ignored command.")

                        ignore_wake_until = time.time() + float(config.get("post_command_wake_lockout_seconds", 4.0))
                        log(config, "State: WAKE_ONLY")
                        continue

                    log(config, "[Vetri] Routing command safely...")

                    return_code, output, summary = run_router(transcript)

                    log(config, "========== Router Output ==========")

                    for line in output.splitlines():
                        log(config, line)

                    log(config, "===================================")
                    log(config, f"[Vetri] Summary: {summary}")

                    maybe_speak_summary(config, summary)

                    if return_code != 0:
                        log(config, f"[Vetri] Router returned non-zero code: {return_code}")

                    reset_wake_model_if_supported(model)
                    drained = drain_audio_queue(audio_queue, max_items=200)

                    if drained:
                        log(config, f"[Vetri] Drained {drained} buffered audio frame(s) after command.")

                    ignore_wake_until = time.time() + float(config.get("post_command_wake_lockout_seconds", 4.0))
                    log(config, "State: WAKE_ONLY")

    except KeyboardInterrupt:
        print("\n[Vetri] Stopped by user.", flush=True)


if __name__ == "__main__":
    main()
