from __future__ import annotations

import subprocess
from typing import Any


class SSHBridgeClient:
    APPROVED_COMMANDS = {
        "export_summary": "~/Ashvath-private-cloud/scripts/export-vetri-summary.sh",
        "cat_export_manifest": "cat ~/Ashvath-private-cloud/exports/for-vetri-ai/export_manifest.json"
    }

    def __init__(self, ssh_host: str = "vetri-mac", enabled: bool = False, timeout_seconds: int = 20) -> None:
        self.ssh_host = ssh_host
        self.enabled = enabled
        self.timeout_seconds = timeout_seconds

    def run_approved(self, command_name: str) -> dict[str, Any]:
        if not self.enabled:
            return {"ok": False, "status": "disabled", "message": "SSH bridge is disabled by default. Use sync script explicitly when needed."}
        command = self.APPROVED_COMMANDS.get(command_name)
        if command is None:
            return {"ok": False, "status": "blocked", "message": "SSH command is not approved."}
        try:
            completed = subprocess.run(["ssh", self.ssh_host, command], capture_output=True, text=True, timeout=self.timeout_seconds)
            return {"ok": completed.returncode == 0, "return_code": completed.returncode, "stdout": completed.stdout[-4000:], "stderr": completed.stderr[-1000:]}
        except Exception as error:
            return {"ok": False, "status": "failed", "message": str(error)}

    def check(self) -> dict[str, Any]:
        return self.run_approved("cat_export_manifest")
