# Vetri — Private Cloud Control Assistant

> Context file for Claude Code. Read this first every session.

## What This Is

Vetri is a **private cloud control assistant + AI companion**, built control-first and safety-first. It lets a user manage a self-hosted private cloud through natural language, but the AI never touches the machine directly — it only suggests an intent label, and local code decides what is allowed to run.

Core principle:
- **OpenAI / LLM** = understands, explains, reasons, talks
- **Local Vetri code (Windows)** = decides what is allowed
- **Mac** = executes only predefined scripts

## Two-Machine Architecture

```
User
 ↓
Windows PC = AI / control brain
  Tailscale IP: 100.99.117.47
  Repo path: Z:\ashvath-private-cloud
 ↓ SSH over Tailscale
MacBook Pro 2016 = execution server
  Tailscale IP: 100.79.123.44
  Repo path: /Users/Ashvath/Ashvath-private-cloud
  SSD: /Volumes/AshvathCloud
 ↓
Docker via Colima
  Immich, Home Assistant, Uptime Kuma, Netdata, Portainer
```

Git is the source of truth for both: `https://github.com/ashvaravi/ashvath-private-cloud`
Workflow: edit → commit → push on one machine → pull on the other.

## The Backend Is the Only Entry Point

The app must NEVER talk directly to Home Assistant, Immich, Docker socket, Portainer, Mac shell scripts, or Tailscale. Everything routes through the FastAPI backend on the Mac, which calls safe service adapters. The backend observes services and hides complexity — it does not own them.

Request flow:
```
App / Vetri → FastAPI route → service function → allowlisted operation → structured JSON
```
Never: API endpoint runs a raw shell command.

## Hard Constraints (NEVER BREAK)

- Mac is an old Intel MacBook Pro 2016 — no heavy AI workloads, no local LLMs on Mac.
- Do not assume modern Python / pip on Mac. Keep Mac scripts simple (write logs, append JSONL, run shell scripts, expose over SSH).
- macOS `pf` firewall is disabled — do NOT modify it unless explicitly asked.
- The AI never generates shell commands. It only returns intent JSON.
- All actions validate against the allowlist before running.
- No secrets ever sent to the LLM (.env, SSH keys, API keys, passwords, photos, videos, DB dumps, full raw logs, full Docker volumes).
- Never touch SSH config or Tailscale ACL casually once remote access works.

## Safety Router (non-negotiable)

Risk model:
- `low` → read-only status → run directly
- `medium` → restart service / trigger scene / mode → require confirmation
- `high` → blocked / manual approval only
- `unknown` → reject

Blocked unless manually added later: delete files, wipe volumes, modify firewall, change Tailscale ACL, edit SSH config, remove Docker volumes, expose public ports, read private media, send secrets to AI, run arbitrary commands, install packages, auto-edit docker-compose.

## AI Tier Strategy

- **Tier 0 — Regex / keyword fast path**: obvious commands (check health, show logs, ssd status, docker status, restart immich). Fast, free, private, stable. Handles most cases.
- **Tier 1 — Local model (optional, Windows)**: e.g. Ollama + small model + forced JSON prompt, for flexible intent classification only.
- **Tier 2 — OpenAI**: reasoning, diagnosis, explanation, planning, summarization, companion behavior. NOT a command executor, memory owner, or file reader.

Reliability trick for local/tiered models: force strict JSON output against the fixed allowed-action set.

## Data Formats

Intent output:
```json
{ "intent": "health_check", "target": "immich", "confidence": 0.92, "requires_confirmation": false, "mode": "control" }
```
Unknown:
```json
{ "intent": "unknown", "target": null, "confidence": 0.0, "requires_confirmation": false, "mode": "clarify" }
```
Confidence rules: `>=0.85` execute if safe · `0.50–0.84` clarify · `<0.50` reject/escalate.

Action definition (vetri_actions.json):
```json
{
  "health_check": {
    "description": "Check private cloud service health",
    "script": "remote-health-check.sh",
    "risk": "low",
    "requires_confirmation": false,
    "write_access": false
  }
}
```

Context packet sent to OpenAI is always sanitized: service status, short error summaries, allowed actions, the user question, non-sensitive metadata, cleaned incident summaries — nothing raw or secret.

Audit log (command_audit.jsonl), one line per action:
```json
{ "timestamp": "...", "user_input": "...", "resolved_intent": "...", "target": "...", "confidence": 0.96, "risk": "low", "confirmation_required": false, "executed": true, "result": "success" }
```

## Windows Project (AI brain)

`Z:\ashvath-private-cloud\application\vetri\`
- `vetri_ai/` — intent router (WORKING)
- `vetri_bridge.py` — SSH execution bridge over Tailscale
- `vetri_actions.json` — safe action allowlist
- `vetri_logs/`, `vetri_memory/`, `vetri_rag/` — local logs, memory, RAG (future)

Memory stays on Windows, never inside OpenAI.

## Mac Project (execution server)

`/Users/Ashvath/Ashvath-private-cloud/application/backend/`
Target structure (layers):
- `routes/` — API endpoints (system, storage, docker, services, backups, home_assistant, modes, dashboard, network, audit)
- `services/` — safe operations (one service module per route + command_runner)
- `schemas/` — structured response models
- `core/` — security, safety, logger, settings, response, exceptions
- `data/` — allowed_actions.json, service_registry.json, dashboard_config.json, mode_registry.json
- `logs/` — app.log, audit.jsonl, errors.log
- `utils/`, `tests/`

Existing Mac scripts (`scripts/`): `remote-health-check.sh`, `view-logs.sh`, `emergency-restart.sh`, `cloudctl.sh`.

## API Surface (versioned)

Use `/api/v1/...` so changes don't break clients.
- `system`: ping, info, health
- `storage`: status, usage, paths — is SSD mounted, used/free, immich-library + backup folders present
- `docker`: containers, status — read-only container health (no restart endpoint yet)
- `services`: status + per-service (immich, homeassistant, uptime-kuma, netdata, portainer) → `{name, status, url, http_code}`
- `backups`: summary + per-target — latest backup time/size/count, accessible, too old?
- `home` / `modes`: entities, toggle, study/sleep/away/all-off (token stays on Mac, never in app)
- `dashboard/summary`: combines everything for the app's first screen
- `audit`: action history

## Service Endpoints (local)

Immich `http://127.0.0.1:2283` · Home Assistant `:8123` · Uptime Kuma `:3001` · Netdata `:19999` · Portainer `:9443`.

## Build Order

Read-only visibility → security → control:
1. API versioning
2. Storage module
3. Docker read-only module
4. Services status module
5. Backup status module
6. Logging
7. Basic API-key security (X-Vetri-API-Key, secrets in backend `.env`)
8. Home Assistant control module
9. Action safety layer for writes
10. Backend run automation (launchd / start script)
11. Dashboard summary endpoint

## Companion + Memory (future, do not over-build)

- RAG = what Vetri knows · fine-tuning = how Vetri behaves · safety router = what Vetri can do.
- Memory pyramid: raw logs → structured events → daily summaries → incident memory → RAG index.
- Retention: raw logs 7–30d, structured events 90–180d, daily summaries 1–3y, incidents permanent.
- Mac = raw operational memory source. Windows = RAG + AI brain. OpenAI = reasoning over selected context.
- Tools considered: sentence-transformers/all-MiniLM-L6-v2 + ChromaDB (CPU-native, small). Avoid LangChain and heavy vector DBs for now.

## Do NOT Build Yet

AI inside backend, RAG, memory, local LLM on Mac, OpenAI calls in backend, Nginx, HTTPS gateway, firewall changes, Dockerizing FastAPI, complex DB, public exposure. Stabilize the read-only foundation first.

## Working Mindset

Collect first. Structure second. Summarize third. Retrieve fourth. Reason fifth. Act last. Don't jump to the final intelligent system before stabilizing the foundation. Don't mix monitoring, RAG, and action execution into one step.

## When Editing

- This is a dual-machine repo. State clearly which file is LOCAL (Windows) vs REMOTE (Mac) in any change.
- After edits: commit + push on the machine you changed, then pull on the other.
- Keep changes read-only-first; gate every write behind confirmation + audit.
