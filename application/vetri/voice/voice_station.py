from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn


VOICE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = VOICE_DIR.parent
STATIC_DIR = VOICE_DIR / "station_static"
STATION_LOG_DIR = VOICE_DIR / "station_logs"
STATION_STATE_PATH = VOICE_DIR / "voice_station_state.json"
WAKE_LISTENER_PATH = VOICE_DIR / "wake_listener.py"

app = FastAPI(title="Vetri Voice Station", version="1.0.1")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class VoiceStation:
    def __init__(self) -> None:
        self.process: subprocess.Popen[str] | None = None
        self.started_at: float | None = None
        self.last_stop_at: float | None = None
        self.last_exit_code: int | None = None
        self.autostart_enabled = False
        self.manual_stop_requested = True

        self.logs: deque[str] = deque(maxlen=1000)
        self.lock = threading.RLock()

        self.reader_thread: threading.Thread | None = None
        self.supervisor_thread: threading.Thread | None = None

        self.station_log_file = STATION_LOG_DIR / "voice_station.log"

    def now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def append_log(self, message: str) -> None:
        clean = str(message).rstrip("\n")

        if not clean:
            return

        stamped = f"{self.now()} | {clean}"

        with self.lock:
            self.logs.append(stamped)

        try:
            STATION_LOG_DIR.mkdir(parents=True, exist_ok=True)
            with self.station_log_file.open("a", encoding="utf-8") as f:
                f.write(stamped + "\n")
        except Exception:
            pass

    def save_state(self) -> None:
        data = {
            "running": self.is_running(),
            "autostart_enabled": self.autostart_enabled,
            "manual_stop_requested": self.manual_stop_requested,
            "last_exit_code": self.last_exit_code,
            "last_stop_at": self.last_stop_at,
            "updated_at_utc": self.now(),
        }

        try:
            STATION_STATE_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    def is_running(self) -> bool:
        with self.lock:
            process = self.process

        if process is None:
            return False

        return process.poll() is None

    def get_uptime_seconds(self) -> int:
        if not self.is_running() or self.started_at is None:
            return 0

        return int(time.time() - self.started_at)

    def find_wake_listener_processes(self) -> list[dict[str, Any]]:
        if not sys.platform.startswith("win"):
            return []

        try:
            ps = (
                "Get-CimInstance Win32_Process | "
                "Where-Object { $_.Name -match 'python' -and $_.CommandLine -like '*wake_listener.py*' } | "
                "Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress"
            )

            result = subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=8,
            )

            raw = result.stdout.strip()

            if not raw:
                return []

            parsed = json.loads(raw)

            if isinstance(parsed, dict):
                return [parsed]

            if isinstance(parsed, list):
                return [item for item in parsed if isinstance(item, dict)]

            return []

        except Exception as exc:
            self.append_log(f"[Station] Could not scan wake listener processes: {exc}")
            return []

    def force_kill_pid_tree(self, pid: int) -> None:
        if sys.platform.startswith("win"):
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                check=False,
            )
        else:
            try:
                os.kill(pid, 15)
            except Exception:
                pass

    def force_stop_all_wake_listeners(self) -> int:
        killed = 0

        # Kill tracked process first.
        with self.lock:
            process = self.process

        if process is not None and process.poll() is None:
            self.append_log(f"[Station] Force killing tracked wake listener PID {process.pid}.")
            self.force_kill_pid_tree(process.pid)
            killed += 1

            try:
                process.wait(timeout=5)
            except Exception:
                pass

        # Kill any orphan wake_listener.py processes.
        for item in self.find_wake_listener_processes():
            try:
                pid = int(item.get("ProcessId"))
            except Exception:
                continue

            self.append_log(f"[Station] Force killing orphan wake listener PID {pid}.")
            self.force_kill_pid_tree(pid)
            killed += 1

        with self.lock:
            if self.process is not None and self.process.poll() is not None:
                self.last_exit_code = self.process.returncode

            self.process = None
            self.last_stop_at = time.time()
            self.manual_stop_requested = True
            self.autostart_enabled = False

        self.save_state()
        return killed

    def start(self, autostart: bool = True) -> tuple[bool, str]:
        if not WAKE_LISTENER_PATH.exists():
            return False, f"wake_listener.py not found at {WAKE_LISTENER_PATH}"

        # Start from clean state.
        self.force_stop_all_wake_listeners()

        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"

        command = [sys.executable, str(WAKE_LISTENER_PATH)]

        try:
            process = subprocess.Popen(
                command,
                cwd=str(PROJECT_ROOT),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                env=env,
            )

            with self.lock:
                self.process = process
                self.started_at = time.time()
                self.last_exit_code = None
                self.manual_stop_requested = False
                self.autostart_enabled = autostart

            self.append_log("[Station] Wake listener started in continuous wake-only mode.")
            self.append_log(f"[Station] PID: {process.pid}")
            self.append_log(f"[Station] Command: {' '.join(command)}")
            self.append_log("[Station] It should wait for wake phrase before routing any command.")

            self.reader_thread = threading.Thread(
                target=self._read_process_output,
                args=(process,),
                daemon=True,
            )
            self.reader_thread.start()

            if self.supervisor_thread is None or not self.supervisor_thread.is_alive():
                self.supervisor_thread = threading.Thread(
                    target=self._supervisor_loop,
                    daemon=True,
                )
                self.supervisor_thread.start()

            self.save_state()
            return True, "Vetri wake listener started."

        except Exception as exc:
            self.append_log(f"[Station] Failed to start wake listener: {exc}")
            self.save_state()
            return False, str(exc)

    def stop(self) -> tuple[bool, str]:
        self.append_log("[Station] Manual stop requested.")
        killed = self.force_stop_all_wake_listeners()
        self.append_log(f"[Station] Manual stop completed. Processes killed: {killed}.")
        return True, f"Vetri wake listener force-stopped. Processes killed: {killed}."

    def restart(self) -> tuple[bool, str]:
        self.append_log("[Station] Restart requested.")
        self.force_stop_all_wake_listeners()
        time.sleep(1.0)
        return self.start(autostart=True)

    def _read_process_output(self, process: subprocess.Popen[str]) -> None:
        if process.stdout is None:
            return

        try:
            for line in process.stdout:
                self.append_log(line)
        except Exception as exc:
            self.append_log(f"[Station] Output reader error: {exc}")

    def _supervisor_loop(self) -> None:
        while True:
            time.sleep(3)

            with self.lock:
                process = self.process
                should_autostart = self.autostart_enabled and not self.manual_stop_requested

            if process is None:
                continue

            exit_code = process.poll()

            if exit_code is None:
                continue

            with self.lock:
                self.last_exit_code = exit_code
                self.process = None

            self.append_log(f"[Station] Wake listener exited. Exit code: {exit_code}")
            self.save_state()

            if should_autostart:
                self.append_log("[Station] Autostart is enabled. Restarting wake listener.")
                time.sleep(2)
                self.start(autostart=True)

    def status(self) -> dict[str, Any]:
        running = self.is_running()
        orphan_processes = self.find_wake_listener_processes()

        return {
            "ok": True,
            "running": running,
            "pid": self.process.pid if running and self.process else None,
            "uptime_seconds": self.get_uptime_seconds(),
            "autostart_enabled": self.autostart_enabled,
            "manual_stop_requested": self.manual_stop_requested,
            "last_exit_code": self.last_exit_code,
            "last_stop_at": self.last_stop_at,
            "wake_listener_path": str(WAKE_LISTENER_PATH),
            "project_root": str(PROJECT_ROOT),
            "orphan_wake_listener_count": len(orphan_processes),
            "orphan_wake_listeners": orphan_processes,
            "mode": "wake_only_until_hey_vetri",
            "updated_at_utc": self.now(),
        }

    def get_logs(self, limit: int = 250) -> list[str]:
        with self.lock:
            return list(self.logs)[-limit:]


station = VoiceStation()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/status")
def api_status() -> JSONResponse:
    return JSONResponse(station.status())


@app.post("/api/start")
def api_start() -> JSONResponse:
    ok, message = station.start(autostart=True)
    return JSONResponse({"ok": ok, "message": message, "status": station.status()})


@app.post("/api/stop")
def api_stop() -> JSONResponse:
    ok, message = station.stop()
    return JSONResponse({"ok": ok, "message": message, "status": station.status()})


@app.post("/api/restart")
def api_restart() -> JSONResponse:
    ok, message = station.restart()
    return JSONResponse({"ok": ok, "message": message, "status": station.status()})


@app.post("/api/force-stop")
def api_force_stop() -> JSONResponse:
    killed = station.force_stop_all_wake_listeners()
    return JSONResponse(
        {
            "ok": True,
            "message": f"Force stop completed. Processes killed: {killed}.",
            "status": station.status(),
        }
    )


@app.get("/api/logs")
def api_logs(limit: int = 250) -> JSONResponse:
    return JSONResponse(
        {
            "ok": True,
            "logs": station.get_logs(limit=limit),
            "status": station.status(),
        }
    )


@app.get("/api/commands")
def api_commands() -> JSONResponse:
    return JSONResponse(
        {
            "ok": True,
            "wake_word": "Hey Vetri",
            "mode": "24/7 wake-only listener. Commands route only after wake phrase detection.",
            "safe_commands": [
                "turn on bedroom light one",
                "turn off bedroom light one",
                "turn on bedroom light two",
                "turn off bedroom light two",
                "turn on bedroom strip light",
                "turn off bedroom strip light",
                "turn on bedroom fan",
                "turn off bedroom fan",
                "turn on bedroom lights",
                "turn off bedroom lights",
                "turn on all bedroom devices",
                "turn off all bedroom devices",
                "home assistant status",
                "show cameras",
                "show unavailable devices",
                "validate endpoints",
                "diagnose backend",
                "diagnose immich",
            ],
            "blocked": [
                "unlock",
                "lock",
                "open door",
                "close door",
                "delete",
                "restart",
                "shutdown",
                "set temperature",
                "arbitrary SSH commands",
                "arbitrary Home Assistant services",
            ],
        }
    )


def main() -> None:
    print("========================================")
    print(" Vetri Voice Station V1A.2-C")
    print("========================================")
    print("Dashboard: http://127.0.0.1:8765")
    print("Mode:      Wake-only until 'Hey Vetri'")
    print("Stop:      Force-kills wake_listener.py process tree")
    print("Safety:    Backend-first Home Assistant control")
    print("========================================")

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8765,
        log_level="warning",
    )


if __name__ == "__main__":
    main()
