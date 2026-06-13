# Vetri AI Phase 3 Final Checkpoint

## Status

Phase 3 is complete after the final smoke test passes.

Phase 3 added OpenAI reasoning safely without giving OpenAI direct execution power.

## Completed Mini-Phases

| Mini-Phase | Name | Status |
|---|---|---|
| 3.0 | OpenAI Safety Design Lock | Complete |
| 3.1 | OpenAI config + safe client skeleton | Complete |
| 3.2 | Sanitized context packet preview | Complete |
| 3.3 | OpenAI diagnosis explanation | Complete |
| 3.4 | OpenAI intent suggestion mode | Complete |
| 3.5 | OpenAI-assisted safe read-only execution | Complete |
| 3.6 | Final smoke test + checkpoint | Complete after test passes |

## Working OpenAI Commands

Explanation commands:

- `explain diagnose immich`
- `explain diagnose backup`
- `explain diagnose storage`
- `explain diagnose network`
- `explain diagnose backend`
- `explain diagnose frontend`

Suggestion-only commands:

- `openai intent why is immich slow`
- `suggest intent for backup looks wrong`
- `ai route frontend is not loading`
- `interpret request tailscale is not working`

OpenAI-assisted read-only execution commands:

- `openai run why is immich slow`
- `openai run backup looks wrong`
- `openai run frontend is not loading`
- `openai run tailscale is not working`

Context preview commands:

- `preview context immich`
- `preview context backup`
- `preview context storage`
- `preview context network`
- `preview context backend`
- `preview context frontend`

## Phase 3 Architecture

User request
?
Local Vetri router
?
Safety router
?
OpenAI receives sanitized context only
?
OpenAI explains or suggests intent
?
Local Vetri validates suggestion
?
Local Vetri executes only approved read-only actions
?
Audit log records everything

## OpenAI Role

OpenAI can:

- Explain diagnosis results
- Summarize safe context
- Suggest structured intent JSON
- Help interpret flexible language
- Recommend safe next checks

OpenAI cannot:

- Execute commands directly
- Call backend directly
- Call Home Assistant directly
- Read secrets
- Read raw logs
- Read photos/videos
- Modify files
- Restart services
- Run backups
- Control devices

## Local Vetri Role

Local Vetri is responsible for:

- Allowlist validation
- Risk validation
- Read-only validation
- Confidence threshold enforcement
- Action-type validation
- Backend calls
- SSH check execution
- Audit logging
- Blocking unsafe requests

## Phase 3.5 Execution Rules

OpenAI-assisted execution is allowed only if:

- Suggested intent exists in `vetri_actions.json`
- Confidence is greater than or equal to threshold
- Risk is low
- Action is read-only
- Action does not require confirmation
- Action type is one of:
  - `diagnosis_skill`
  - `backend_api`
  - `ssh_check`

## Still Blocked

- Home Assistant control
- Device control
- Write actions
- Restart actions
- Backup execution
- File modification
- Arbitrary shell commands
- Arbitrary SSH commands
- RAG
- Memory writes
- Voice

## Home Assistant Long-Term Direction

Vetri is not only a troubleshooting assistant.

The long-term goal is for Vetri to become the AI orchestration layer over Home Assistant, eventually usable like an Alexa-style voice assistant.

Future Home Assistant control must use:

- Device registry
- Entity allowlist
- Action allowlist
- Room/group mapping
- Risk levels
- Confirmation gates
- State check before control
- Post-action verification
- Audit logging

Home Assistant controls devices.

Vetri reasons, routes, validates, confirms, and explains.

## Next Major Options

After Phase 3, the next major direction can be one of:

1. Phase 4 — Logging, event history, and safe memory preparation.
2. Phase 5 — Memory/RAG layer.
3. Home Assistant control phase — read-only entity registry first.
4. Voice phase — mic/speaker interaction after control architecture is safe.

Recommended next step:

Start with Home Assistant read-only device/entity discovery before write/control actions.

Why:

This supports the final Alexa-style goal while preserving safety.
