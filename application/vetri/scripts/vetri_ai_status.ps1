$Root = "Z:\HomeLLM"
Set-Location $Root

Write-Host "===== Vetri AI Project Status ====="
Write-Host ""
Write-Host "Root: $Root"
Write-Host ""
Write-Host "Completed:"
Write-Host "- Phase 1B: Safe backend-integrated CLI"
Write-Host "- Phase 2: Read-only diagnosis layer"
Write-Host "- Phase 3: OpenAI reasoning layer, after final smoke test passes"
Write-Host ""
Write-Host "Core checkpoint files:"

$Files = @(
    "PHASE_1B_CHECKPOINT.md",
    "PHASE_2_CHECKPOINT.md",
    "PHASE_3_DESIGN.md",
    "PHASE_3_CHECKPOINT.md",
    "ARCHITECTURE_LOCK.md",
    "config\vetri_actions.json",
    "config\vetri_skills.json",
    "config\vetri_policy.json",
    "config\openai_policy.json",
    "config\openai_config.json"
)

foreach ($File in $Files) {
    if (Test-Path "$Root\$File") {
        Write-Host "[OK] $File"
    } else {
        Write-Host "[FAIL] $File"
    }
}

Write-Host ""
Write-Host "Recommended checks:"
Write-Host "powershell -ExecutionPolicy Bypass -File Z:\HomeLLM\scripts\smoke_test_phase3_final.ps1"
Write-Host "powershell -ExecutionPolicy Bypass -File Z:\HomeLLM\scripts\run_vetri_ai.ps1"
