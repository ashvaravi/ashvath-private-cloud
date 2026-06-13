# Vetri AI Phase 1B Checkpoint

## Status

Phase 1B is complete.

This phase created the laptop-side Vetri AI safe command skeleton.

## Completed Capabilities

- Seamless SSH alias: `vetri-mac`
- Modular `Z:\HomeLLM` structure
- Legacy prototype preserved under `legacy/`
- `.env` support for backend URL and API key
- Backend API client
- SSH connectivity check client
- Intent router
- Safety router
- Policy engine
- Confirmation-ready risk model
- Audit logger
- Help command
- Action list command
- Phase status command
- Endpoint validation command
- Human-readable output mode
- JSON debug mode

## Working Commands

- `help`
- `list actions`
- `phase status`
- `validate endpoints`
- `backend ping`
- `cloud status`
- `storage status`
- `backup status`
- `network status`
- `ssh check`
- `json cloud status`
- `json backup status`
- `json network status`
- `json validate endpoints`

## Current Architecture

Laptop / PC:
- AI brain
- Command router
- Safety router
- Backend client
- Future OpenAI/RAG/memory host

Mac:
- Execution server
- FastAPI backend
- Docker services
- Home Assistant
- Immich
- Uptime Kuma
- Netdata
- Portainer
- Approved scripts

Primary communication:
Laptop Vetri AI -> Mac FastAPI backend over Tailscale

Fallback communication:
Laptop Vetri AI -> SSH alias `vetri-mac`

## Current Safety Rules

- No OpenAI yet
- No RAG yet
- No memory updates yet
- No voice yet
- No arbitrary shell execution
- No automatic restart actions
- No high-risk actions
- No secret reading
- No raw log indexing
- No file deletion

## Phase 1B Final Principle

Vetri can observe and summarize safely.
Vetri cannot modify or restart anything yet.

## Next Phase

Phase 2: Read-only diagnosis skills.

Planned Phase 2 commands:
- `diagnose immich`
- `diagnose backup`
- `diagnose storage`
- `diagnose network`
- `diagnose backend`
- `diagnose frontend`

Phase 2 must remain read-only.
No write actions.
No restarts.
No OpenAI.
No RAG.

## Phase 1B.6 Addendum

Completed:
- Natural phrase aliases
- Required-term local intent matching
- Better support for human prompts without OpenAI

Examples now supported:
- `what is the state of the cloud backup`
- `how are my backups`
- `is my SSD mounted`
- `how is my private cloud`
- `are all services online`
- `is tailscale working`
- `can you reach the mac`

This still uses only local routing.
OpenAI is not enabled yet.
