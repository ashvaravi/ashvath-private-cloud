from __future__ import annotations

import base64
import json
import os
import secrets
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
VOICE_DIR = Path(__file__).resolve().parent
TOKEN_PATH = VOICE_DIR / "spotify_token.json"

DEFAULT_REDIRECT_URI = "http://127.0.0.1:8888/callback"

SCOPES = [
    "user-read-playback-state",
    "user-modify-playback-state",
    "user-read-currently-playing",
    "user-read-private",
]


def load_environment() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    load_dotenv(VOICE_DIR / ".env")


def get_required_env(name: str) -> str:
    value = os.getenv(name, "").strip()

    if not value:
        raise RuntimeError(f"{name} is missing. Add it to Z:\\HomeLLM\\.env")

    return value


def build_basic_auth_header(client_id: str, client_secret: str) -> str:
    raw = f"{client_id}:{client_secret}".encode("utf-8")
    encoded = base64.b64encode(raw).decode("utf-8")
    return f"Basic {encoded}"


class CallbackHandler(BaseHTTPRequestHandler):
    auth_code: str | None = None
    auth_state: str | None = None
    auth_error: str | None = None

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed.query)

        CallbackHandler.auth_code = query.get("code", [None])[0]
        CallbackHandler.auth_state = query.get("state", [None])[0]
        CallbackHandler.auth_error = query.get("error", [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()

        if CallbackHandler.auth_error:
            html = """
            <html>
              <body>
                <h2>Vetri Spotify authorization failed.</h2>
                <p>You can close this tab and return to PowerShell.</p>
              </body>
            </html>
            """
        else:
            html = """
            <html>
              <body>
                <h2>Vetri Spotify authorization completed.</h2>
                <p>You can close this tab and return to PowerShell.</p>
              </body>
            </html>
            """

        self.wfile.write(html.encode("utf-8"))

    def log_message(self, format: str, *args: Any) -> None:
        return


def wait_for_callback(expected_state: str, host: str = "127.0.0.1", port: int = 8888) -> str:
    server = HTTPServer((host, port), CallbackHandler)
    print("[Vetri Spotify] Waiting for Spotify login callback...")
    server.handle_request()
    server.server_close()

    if CallbackHandler.auth_error:
        raise RuntimeError(f"Spotify authorization failed: {CallbackHandler.auth_error}")

    if not CallbackHandler.auth_code:
        raise RuntimeError("No authorization code received from Spotify.")

    if CallbackHandler.auth_state != expected_state:
        raise RuntimeError("Spotify authorization state mismatch. Refusing token exchange.")

    return CallbackHandler.auth_code


def exchange_code_for_token(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> dict[str, Any]:
    data = urllib.parse.urlencode(
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
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
        payload = response.read().decode("utf-8")

    return json.loads(payload)


def save_token(token: dict[str, Any]) -> None:
    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)

    with TOKEN_PATH.open("w", encoding="utf-8") as f:
        json.dump(token, f, indent=2)

    print(f"[Vetri Spotify] Token saved to: {TOKEN_PATH}")


def main() -> None:
    load_environment()

    client_id = get_required_env("SPOTIFY_CLIENT_ID")
    client_secret = get_required_env("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI", DEFAULT_REDIRECT_URI).strip() or DEFAULT_REDIRECT_URI

    state = secrets.token_urlsafe(24)
    scope = " ".join(SCOPES)

    params = urllib.parse.urlencode(
        {
            "response_type": "code",
            "client_id": client_id,
            "scope": scope,
            "redirect_uri": redirect_uri,
            "state": state,
            "show_dialog": "true",
        }
    )

    auth_url = f"https://accounts.spotify.com/authorize?{params}"

    print("========================================")
    print(" Vetri Spotify Authorization")
    print("========================================")
    print("A browser window will open.")
    print("Log in to Spotify and approve the requested permissions.")
    print("Redirect URI must be configured in Spotify Developer Dashboard as:")
    print(redirect_uri)
    print("========================================")

    webbrowser.open(auth_url)

    code = wait_for_callback(expected_state=state)

    print("[Vetri Spotify] Authorization code received.")
    token = exchange_code_for_token(
        code=code,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
    )

    save_token(token)

    print("[Vetri Spotify] Authorization complete.")


if __name__ == "__main__":
    main()
