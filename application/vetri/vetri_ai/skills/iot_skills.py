from __future__ import annotations


def home_control_scaffold() -> dict[str, object]:
    return {"ok": False, "status": "confirmation_required", "message": "Home control must go through the Mac backend verified endpoint and is not executed by chat by default."}
