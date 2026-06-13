from __future__ import annotations

import subprocess


def _escape_for_powershell_single_quote(text: str) -> str:
    """
    PowerShell single-quoted strings escape ' as ''.
    """
    return str(text).replace("'", "''")


def speak(
    text: str,
    enabled: bool = True,
    rate: int = 0,
    volume: int = 90,
    wait: bool = False,
) -> bool:
    """
    Local Windows text-to-speech helper for Vetri.

    Uses Windows built-in System.Speech through PowerShell.
    No cloud API is used.
    No popup/window is required.
    """

    if not enabled:
        return False

    clean_text = str(text or "").strip()

    if not clean_text:
        return False

    clean_text = clean_text.replace("\n", " ")
    clean_text = " ".join(clean_text.split())

    # Keep responses short so Vetri does not become noisy.
    if len(clean_text) > 220:
        clean_text = clean_text[:220].rsplit(" ", 1)[0] + "."

    safe_rate = max(-5, min(5, int(rate)))
    safe_volume = max(0, min(100, int(volume)))
    safe_text = _escape_for_powershell_single_quote(clean_text)

    ps_script = f"""
Add-Type -AssemblyName System.Speech;
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer;
$speaker.Rate = {safe_rate};
$speaker.Volume = {safe_volume};
$speaker.Speak('{safe_text}');
"""

    try:
        if wait:
            subprocess.run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    ps_script,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        else:
            subprocess.Popen(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-Command",
                    ps_script,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        return True

    except Exception:
        return False


def speak_command_result(
    summary: str,
    enabled: bool = True,
    rate: int = 0,
    volume: int = 90,
) -> bool:
    """
    Speaks only a short final command result.
    """

    clean_summary = str(summary or "").strip()

    if not clean_summary:
        return speak(
            "Done.",
            enabled=enabled,
            rate=rate,
            volume=volume,
            wait=False,
        )

    lower = clean_summary.lower()

    if "failed" in lower or "error" in lower or "could not" in lower:
        return speak(
            "I could not complete that command.",
            enabled=enabled,
            rate=rate,
            volume=volume,
            wait=False,
        )

    if len(clean_summary) > 220:
        clean_summary = clean_summary[:220].rsplit(" ", 1)[0] + "."

    return speak(
        clean_summary,
        enabled=enabled,
        rate=rate,
        volume=volume,
        wait=False,
    )


if __name__ == "__main__":
    speak("Vetri voice response is working.", enabled=True, rate=0, volume=90, wait=True)
