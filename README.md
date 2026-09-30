Vetri — A Safety-First AI Control Assistant for a Private Cloud

Manage a self-hosted private cloud in plain English, without ever letting the AI touch the machine.

Vetri lets you say things like "check health", "show logs", or "restart Immich". A language model helps interpret what you mean, but it never writes or runs a command. It only proposes an intent label. Local code checks that label against an allowlist and decides whether it may run.

The AI understands. The local code decides. The server only executes pre-approved scripts.

Why this exists

Giving an LLM shell access to your own infrastructure is convenient and risky. Vetri takes the opposite approach: control first, safety first.

The model can explain, reason, and talk, but it has no execution path.
Every action is a named entry in an allowlist with a declared risk level.
Anything unknown is rejected by default.
Every decision is written to an audit log.

It runs on a real home setup: an older Intel MacBook Pro hosts the services, and a separate Windows PC is the "brain".

Architecture
MacBook Pro 2016 — execution server
Windows PC — AI / control brain
SSH over Tailscale
User
Intent router(Tier 0 keyword → Tier 1local model → Tier 2OpenAI)
Safety router(allowlist + risk check)
SSH bridge
Logs · memory · RAG(future)
FastAPI backend (/api/v1)
Predefined shell scripts
Docker via ColimaImmich · Home Assistant ·Uptime Kuma · Netdata ·Portainer
Layer	Machine	Responsibility
AI brain	Windows PC	Interprets requests, applies safety rules, keeps memory and logs
Execution server	MacBook Pro (Intel, 2016)	Runs only predefined scripts; exposes a read-only-first API
Services	Docker via Colima on the Mac	Immich, Home Assistant, Uptime Kuma, Netdata, Portainer
Network	Tailscale	Private connectivity between the two machines

Git is the source of truth for both machines: edit, commit, and push on one, then pull on the other.

How a request flows
"restart immich"
   │
   ▼  Tier 0 keyword match (no LLM needed)
{ "intent": "restart_service", "target": "immich",
  "confidence": 0.96, "requires_confirmation": true, "mode": "control" }
   │
   ▼  Safety router: is the intent in the allowlist? what is its risk?
risk = medium  →  ask the user to confirm
   │
   ▼  User confirms
SSH bridge → predefined script on the Mac → structured JSON result
   │
   ▼  Audit log entry written (allowed or blocked)

If the input doesn't match anything known:

json
{ "intent": "unknown", "target": null, "confidence": 0.0,
  "requires_confirmation": false, "mode": "clarify" }
The safety model
Risk levels
Risk	Examples	Behavior
Low	Read-only status, health checks, logs	Runs directly
Medium	Restart a service, trigger a scene or mode	Requires confirmation
High	Delete files, wipe volumes, change firewall/SSH/Tailscale ACL	Blocked by default; manual approval only
Unknown	Anything not in the allowlist	Rejected
Confidence rules
Confidence	Action
≥ 0.85	Execute, if the action is safe
0.50 – 0.84	Ask the user to clarify
< 0.50	Reject or escalate
Hard rules
The AI never generates shell commands. It only returns intent JSON.
Every action is validated against the allowlist before it runs.
No secrets are ever sent to the LLM: .env files, SSH keys, API keys, passwords, photos, videos, database dumps, or raw logs.
The app never talks directly to Home Assistant, Immich, the Docker socket, Portainer, or Tailscale. It goes through the backend only.
An API endpoint never runs a raw shell command.
Action allowlist

Each allowed action is declared in vetri_actions.json:

json
{
  "health_check": {
    "description": "Check private cloud service health",
    "script": "remote-health-check.sh",
    "risk": "low",
    "requires_confirmation": false,
    "write_access": false
  }
}
Audit log

Every request produces one line in command_audit.jsonl:

json
{ "timestamp": "...", "user_input": "...", "resolved_intent": "health_check",
  "target": "immich", "confidence": 0.96, "risk": "low",
  "confirmation_required": false, "executed": true, "result": "success" }
Three-tier AI routing

Handling requests in cheap, private tiers first keeps the system fast and predictable.

Tier	What it uses	Used for
0	Regex / keyword fast path	Obvious commands (health, logs, SSD status, restart X). Free, private, stable. Handles most requests.
1	Small local model via Ollama (optional, on Windows)	Flexible intent classification only, with strict JSON output against the fixed action set
2	OpenAI API	Diagnosis, explanation, planning, summarization. Never executes commands and never owns memory.

Any context sent to OpenAI is a sanitized packet: service status, short error summaries, the allowed actions, the user's question, and non-sensitive metadata.

Backend API (Mac, FastAPI)

The API is versioned under /api/v1/ so clients don't break when it changes. It observes services and hides their complexity; it does not own them.

Area	What it exposes
system	ping, info, health
storage	SSD mounted, used/free space, library and backup folders present
docker	Read-only container status
services	Status of Immich, Home Assistant, Uptime Kuma, Netdata, Portainer
backups	Latest backup time, size, count, and whether it is too old
home / modes	Home Assistant entities and modes such as study, sleep, away, all-off
dashboard/summary	Combined view for the app's first screen
audit	Action history
Project layout

Windows (AI brain)

application/vetri/
├── vetri_ai/          # intent router
├── vetri_bridge.py    # SSH execution bridge over Tailscale
├── vetri_actions.json # safe action allowlist
├── vetri_logs/        # audit and runtime logs
├── vetri_memory/      # local memory (future)
└── vetri_rag/         # RAG index (future)

Mac (execution server)

application/backend/
├── routes/     # API endpoints
├── services/   # safe operations + command runner
├── schemas/    # structured response models
├── core/       # security, safety, logger, settings, exceptions
├── data/       # allowed_actions, service_registry, dashboard_config, mode_registry
├── logs/       # app.log, audit.jsonl, errors.log
├── utils/
└── tests/
scripts/        # remote-health-check.sh, view-logs.sh, emergency-restart.sh, cloudctl.sh
Design decisions worth a look
Intent labels, not commands. The model's only power is choosing from a fixed set. A wrong or manipulated answer can at worst select a safe, known action.
Read-only first. Visibility comes before control, and every write path is gated by confirmation and audit.
Constraint-driven design. The Mac is a 2016 Intel machine, so it runs no local LLMs and only simple scripts. All AI work lives on the Windows side.
Memory stays local. Logs and memory live on Windows and are never owned by an external model.
A staged intelligence model: collect → structure → summarize → retrieve → reason → act. Each stage is stabilized before the next one is added.
Tech stack

Python · FastAPI · SSH · Tailscale · Docker (Colima) · Ollama (optional local model) · OpenAI API · Bash · JSONL logging

Services managed: Immich · Home Assistant · Uptime Kuma · Netdata · Portainer

Status and roadmap
 Intent router (Tier 0 keyword path)
 API versioning
 Storage, Docker (read-only), services, and backup status modules
 Structured logging
 API-key security (X-Vetri-API-Key)
 Home Assistant control module
 Safety layer for write actions
 Backend start automation (launchd)
 Dashboard summary endpoint
 Companion and memory layer (logs → events → summaries → incidents → RAG)

Tick the boxes above to match the repo's real state.

Getting started

Fill in the exact steps for your setup. Suggested outline:

Clone the repo on both machines.
Mac: create the backend .env (API key, service URLs) and start the backend.
Windows: configure the SSH host and key for the Mac over Tailscale, and set your OpenAI key.
Run the intent router and try a read-only command such as check health.

Secrets live in .env files that are not committed. See .env.example.

Security notes
Secrets are never committed and never sent to a model.
The backend is not exposed publicly; access is over Tailscale only.
Firewall, SSH config, and Tailscale ACLs are deliberately outside the AI's reach.
