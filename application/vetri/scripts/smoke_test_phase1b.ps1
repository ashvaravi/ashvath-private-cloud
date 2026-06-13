$Root = "Z:\HomeLLM"
Set-Location $Root

Write-Host "===== Vetri AI Phase 1B.4 Smoke Test ====="

Write-Host ""
Write-Host "Test 1: SSH alias"
ssh vetri-mac "hostname; whoami; pwd"

Write-Host ""
Write-Host "Test 2: Python module import"
python -c "from vetri_ai.main import run_once; from vetri_ai.utils.formatters import format_human_result; print('import ok')"

Write-Host ""
Write-Host "Test 3: Help command human format"
python -c "from vetri_ai.main import run_once; from vetri_ai.utils.formatters import format_human_result; print(format_human_result(run_once('help')))"

Write-Host ""
Write-Host "Test 4: Endpoint validation human format"
python -c "from vetri_ai.main import run_once; from vetri_ai.utils.formatters import format_human_result; print(format_human_result(run_once('validate endpoints')))"

Write-Host ""
Write-Host "Test 5: Cloud status human format"
python -c "from vetri_ai.main import run_once; from vetri_ai.utils.formatters import format_human_result; print(format_human_result(run_once('cloud status')))"

Write-Host ""
Write-Host "Test 6: Cloud status JSON still works"
python -c "from vetri_ai.main import run_once; import json; print(json.dumps(run_once('cloud status'), indent=2))"

Write-Host ""
Write-Host "Smoke test completed."
