$Root = "Z:\HomeLLM"
Set-Location $Root

Write-Host "========================================"
Write-Host " Vetri AI Phase 2.3 Metadata Diagnosis Test"
Write-Host "========================================"

$Commands = @(
    "diagnose immich",
    "diagnose backup",
    "diagnose storage",
    "diagnose network",
    "diagnose backend",
    "diagnose frontend"
)

foreach ($Command in $Commands) {
    Write-Host ""
    Write-Host "---- $Command ----"
    python -c "from vetri_ai.main import run_once; from vetri_ai.utils.formatters import format_human_result; print(format_human_result(run_once('$Command')))"
}

Write-Host ""
Write-Host "Phase 2.3 metadata diagnosis test completed."
