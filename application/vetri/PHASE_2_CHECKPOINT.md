# Vetri AI Phase 2 Checkpoint

## Phase 2.1 Status

Read-only diagnosis skills added.

## Added Files

- `config/vetri_skills.json`
- `vetri_ai/skills/skill_runner.py`
- `scripts/smoke_test_phase2_diagnosis.ps1`

## Added Commands

- `diagnose immich`
- `diagnose backup`
- `diagnose storage`
- `diagnose network`
- `diagnose backend`
- `diagnose frontend`

## Safety Rules

- Diagnosis skills are read-only.
- Each skill step must map to an existing allowlisted action.
- Skills cannot execute arbitrary commands.
- Skills cannot run write-access actions.
- Skills cannot restart services.
- Skills cannot trigger backups.
- Skills cannot use OpenAI.
- Skills cannot use RAG.
- Skills cannot update memory.

## Current Goal

Vetri can now run multi-step safe checks and summarize findings.

## Phase 2.2 Status

Diagnosis quality improved.

Added:
- `vetri_ai/skills/diagnosis_interpreter.py`
- Rule-based assessment
- Reasoning section
- Issues section
- Recommended next steps section

Still not enabled:
- OpenAI
- RAG
- Memory writes
- Restarts
- Backup execution
- Any write action

## Phase 2.3 Status

Diagnosis skill metadata added.

Added:
- Service name
- Category
- Severity if failed
- Expected healthy signals
- Possible causes if unhealthy
- Safe next checks

Purpose:
Vetri can now produce more service-aware diagnosis summaries without OpenAI.

Still read-only:
- No restart
- No backup execution
- No file modification
- No OpenAI
- No RAG
- No memory writes

## Phase 2.4 Status

Diagnosis validation and guardrails added.

Added:
- `vetri_ai/skills/skill_validator.py`
- `validate skills` command
- Guardrail validation for all diagnosis workflows

Checks:
- Every skill is read-only
- Every step exists in `vetri_actions.json`
- Every step is read-only
- Every step uses allowed action type
- Diagnosis backend API steps must use GET
- Diagnosis skill steps must remain low risk

Still read-only:
- No restart
- No backup execution
- No file modification
- No arbitrary SSH command
- No OpenAI
- No RAG
- No memory writes

## Phase 2.5 Status

Natural diagnosis phrasing added.

Examples now routed locally:
- `why is immich slow`
- `immich is not opening`
- `photo backup not working`
- `backup looks wrong`
- `why are backups failing`
- `is my ssd having issues`
- `external ssd not mounted`
- `tailscale is not working`
- `remote access not working`
- `backend seems down`
- `api not working`
- `frontend is not loading`
- `ui not opening`
- `vetri app not working`

Still local only:
- No OpenAI
- No RAG
- No memory writes
- No write actions
