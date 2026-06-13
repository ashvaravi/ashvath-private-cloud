from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class BackendClient:
    SAFE_GET_ENDPOINTS = {
        "/",
        "/api/v1/dashboard/summary",
        "/api/v1/network/status",
        "/api/v1/storage/status",
        "/api/v1/backups/summary"
    }

    def __init__(self, base_url: str, api_key: str = "", timeout_seconds: int = 8) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    def safe_get(self, endpoint: str) -> dict[str, Any]:
        if endpoint not in self.SAFE_GET_ENDPOINTS:
            return {"ok": False, "status": "blocked", "message": "Endpoint is not in the safe GET allowlist."}
        return self.request("GET", endpoint)

    def request(self, method: str, endpoint: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        method = method.upper()
        if method != "GET" and not endpoint.startswith("/api/v1/home/control"):
            return {"ok": False, "status": "blocked", "message": "Only safe GET and backend-routed Home Assistant control endpoints are supported."}

        url = f"{self.base_url}{endpoint}"
        headers = {"Accept": "application/json"}
        if self.api_key and self.api_key != "PASTE_YOUR_BACKEND_API_KEY_HERE":
            headers["X-Vetri-API-Key"] = self.api_key

        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"

        try:
            request = urllib.request.Request(url=url, data=body, headers=headers, method=method)
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8", errors="replace")
                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    data = {"text": raw[:1000]}
                return {"ok": 200 <= response.status < 300, "status_code": response.status, "endpoint": endpoint, "data": data}
        except urllib.error.HTTPError as error:
            if error.code in {401, 403}:
                status = "auth_required"
            else:
                status = "http_error"
            return {"ok": False, "status": status, "status_code": error.code, "endpoint": endpoint}
        except Exception as error:
            return {"ok": False, "status": "unreachable", "status_code": None, "endpoint": endpoint, "message": str(error)}

    def home_control_verified(self, payload: dict[str, Any], confirmed: bool = False) -> dict[str, Any]:
        if not confirmed:
            return {"ok": False, "status": "confirmation_required", "message": "Home control requires explicit confirmation and backend verification."}
        return self.request("POST", "/api/v1/home/control/verified", payload)
