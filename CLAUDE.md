\# Vetri Private Cloud - Project Context



\## Architecture

\- Windows (Z:\\ashvath-private-cloud) = AI brain (Vetri intent router, RAG, bridge)

\- Mac (100.79.123.44:/Users/Ashvath/Ashvath-private-cloud) = execution server (FastAPI, Docker, Home Assistant, Immich)

\- Connected via Tailscale SSH

\- Git repo: https://github.com/ashvaravi/ashvath-private-cloud



\## Windows Project Structure

\- application/vetri/vetri\_ai/ → Vetri intent router (WORKING)

\- application/vetri/vetri\_actions.json → safe allowed actions

\- application/vetri/vetri\_bridge.py → SSH execution bridge



\## Mac Project Structure  

\- application/backend/main.py → FastAPI entry point (WORKING)

\- application/backend/routes/ → API endpoints

\- application/backend/services/ → business logic

\- scripts/ → shell scripts called by backend



\## Key Rules (NEVER BREAK THESE)

\- AI never generates shell commands directly

\- All actions go through vetri\_actions.json allowlist

\- Medium risk actions require confirmation

\- No secrets ever sent to OpenAI

\- Mac firewall and SSH config are never touched



\## Current Status

\- Backend running on port 8000

\- Vetri intent routing working

\- Both connected via Git



\## What Needs Building Next

\- Ask me what to build

