# Vetri AI Windows Brain

This repository contains the Windows-side Vetri AI brain foundation for Ashvath Private Cloud + Vetri AI.

Windows is the AI brain and stable local voice runtime. The MacBook is the execution server. The Mac FastAPI backend is the primary control gateway. Home Assistant control must go through the Mac backend; Windows must never directly call Home Assistant.

The stable voice assistant remains in `voice\` and is intentionally not moved or rewritten. `vetri_ai\voice` is only a future integration hook.

## Quick Checks

```powershell
python .\scripts\smoke_test_vetri_ai.py
python -m vetri_ai.cli ask "explain my private cloud architecture"
python -m vetri_ai.cli ask "summarize the latest Mac export"
python -m vetri_ai.cli ask "delete all logs"
```

## Mac Export Sync

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\sync_from_mac.ps1
python .\scripts\sanitize_imports.py
python .\scripts\build_daily_summary.py
python .\scripts\rebuild_rag_index.py
```

If the Mac is unreachable, sync logs a warning and local Vetri AI tests can still run.

## Safety

OpenAI is disabled by default. It can only receive sanitized context packets when explicitly configured. It never executes actions. Local Vetri policy, safety routing, backend verification, and audit logging govern execution.
