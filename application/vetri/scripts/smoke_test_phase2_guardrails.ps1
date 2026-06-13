$Root = "Z:\HomeLLM"
Set-Location $Root

Write-Host "========================================"
Write-Host " Vetri AI Phase 2.4 Guardrail Test"
Write-Host "========================================"

Write-Host ""
Write-Host "---- Syntax checks ----"
python -m py_compile Z:\HomeLLM\vetri_ai\skills\skill_validator.py
python -m py_compile Z:\HomeLLM\vetri_ai\main.py
python -m py_compile Z:\HomeLLM\vetri_ai\utils\formatters.py

Write-Host ""
Write-Host "---- validate skills ----"
python -c "from vetri_ai.main import run_once; from vetri_ai.utils.formatters import format_human_result; print(format_human_result(run_once('validate skills')))"

Write-Host ""
Write-Host "---- json validate skills ----"
python -c "from vetri_ai.main import run_once; import json; print(json.dumps(run_once('validate skills'), indent=2))"

Write-Host ""
Write-Host "---- confirm diagnosis still runs ----"
python -c "from vetri_ai.main import run_once; from vetri_ai.utils.formatters import format_human_result; print(format_human_result(run_once('diagnose immich')))"

Write-Host ""
Write-Host "Phase 2.4 guardrail test completed."
