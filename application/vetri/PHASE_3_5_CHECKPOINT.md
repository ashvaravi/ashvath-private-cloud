# Vetri AI Phase 3.5 Checkpoint

## Status

Phase 3.5 adds OpenAI-assisted read-only execution.

## New Command Pattern

- `openai run why is immich slow`
- `openai run backup looks wrong`
- `openai run frontend is not loading`
- `openai run tailscale is not working`

## Flow

User request
?
OpenAI suggests structured intent
?
Local Vetri validates:
- allowlisted intent
- confidence threshold
- low risk
- read-only
- no confirmation needed
- allowed executable action type
?
Local Vetri executes the allowlisted read-only action
?
Audit log records the suggestion, validation, and execution

## Allowed Action Types

- `diagnosis_skill`
- `backend_api`
- `ssh_check`

## Still Blocked

- Home Assistant control
- Write actions
- Restarts
- Backup execution
- File modification
- Arbitrary SSH commands
- RAG
- Memory writes
- Voice

## Important Rule

OpenAI still does not execute anything directly.

OpenAI suggests.

Local Vetri validates and executes only safe read-only actions.
