$Root = "Z:\HomeLLM"
Set-Location $Root

Write-Host "========================================"
Write-Host " Vetri AI Phase 1B Final Smoke Test"
Write-Host "========================================"

$Failures = 0

function Run-Test {
    param(
        [string]$Name,
        [scriptblock]$Command
    )

    Write-Host ""
    Write-Host "---- $Name ----"

    try {
        & $Command
        if ($LASTEXITCODE -ne $null -and $LASTEXITCODE -ne 0) {
            Write-Host "[FAIL] $Name"
            $script:Failures += 1
        } else {
            Write-Host "[OK] $Name"
        }
    } catch {
        Write-Host "[FAIL] $Name"
        Write-Host $_
        $script:Failures += 1
    }
}

Run-Test "SSH alias vetri-mac" {
    ssh vetri-mac "hostname; whoami; pwd"
}

Run-Test "Python imports" {
    python -c "from vetri_ai.main import run_once; from vetri_ai.utils.formatters import format_human_result; print('import ok')"
}

Run-Test "Help command" {
    python -c "from vetri_ai.main import run_once; from vetri_ai.utils.formatters import format_human_result; print(format_human_result(run_once('help')))"
}

Run-Test "Phase status command" {
    python -c "from vetri_ai.main import run_once; from vetri_ai.utils.formatters import format_human_result; print(format_human_result(run_once('phase status')))"
}

Run-Test "List actions command" {
    python -c "from vetri_ai.main import run_once; from vetri_ai.utils.formatters import format_human_result; print(format_human_result(run_once('list actions')))"
}

Run-Test "Endpoint validation command" {
    python -c "from vetri_ai.main import run_once; from vetri_ai.utils.formatters import format_human_result; print(format_human_result(run_once('validate endpoints')))"
}

Run-Test "Cloud status command" {
    python -c "from vetri_ai.main import run_once; from vetri_ai.utils.formatters import format_human_result; print(format_human_result(run_once('cloud status')))"
}

Run-Test "Storage status command" {
    python -c "from vetri_ai.main import run_once; from vetri_ai.utils.formatters import format_human_result; print(format_human_result(run_once('storage status')))"
}

Run-Test "Backup status command" {
    python -c "from vetri_ai.main import run_once; from vetri_ai.utils.formatters import format_human_result; print(format_human_result(run_once('backup status')))"
}

Run-Test "Network status command" {
    python -c "from vetri_ai.main import run_once; from vetri_ai.utils.formatters import format_human_result; print(format_human_result(run_once('network status')))"
}

Run-Test "SSH check command through Vetri AI" {
    python -c "from vetri_ai.main import run_once; from vetri_ai.utils.formatters import format_human_result; print(format_human_result(run_once('ssh check')))"
}

Run-Test "JSON debug mode backend call" {
    python -c "from vetri_ai.main import run_once; import json; print(json.dumps(run_once('json cloud status'.replace('json ', '')), indent=2))"
}

Write-Host ""
Write-Host "========================================"
if ($Failures -eq 0) {
    Write-Host "[OK] Phase 1B final smoke test passed."
    Write-Host "Phase 1B is ready to close."
} else {
    Write-Host "[FAIL] Phase 1B smoke test completed with $Failures failure(s)."
}
Write-Host "========================================"

exit $Failures
