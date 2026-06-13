$Root = "Z:\HomeLLM"
Set-Location $Root

Write-Host "========================================"
Write-Host " Vetri AI Phase 3.5 Safe Execution Test"
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

Run-Test "Python syntax - main.py" {
    python -m py_compile Z:\HomeLLM\vetri_ai\main.py
}

Run-Test "Advisory mode still does not execute" {
    python -c "from vetri_ai.main import run_once; r=run_once('openai intent why is immich slow'); print(r.get('message')); raise SystemExit(0 if r.get('executed_suggested_intent') is False else 1)"
}

Run-Test "OpenAI-assisted run - immich" {
    python -c "from vetri_ai.main import run_once; r=run_once('openai run why is immich slow'); print(r.get('message')); print('executed=', r.get('executed_suggested_intent')); raise SystemExit(0 if r.get('executed_suggested_intent') is True and r.get('execution_result') else 1)"
}

Run-Test "OpenAI-assisted run - backup" {
    python -c "from vetri_ai.main import run_once; r=run_once('openai run backup looks wrong'); print(r.get('message')); print('executed=', r.get('executed_suggested_intent')); raise SystemExit(0 if r.get('executed_suggested_intent') is True and r.get('execution_result') else 1)"
}

Run-Test "JSON execution boundary" {
    python -c "from vetri_ai.main import run_once; import json; r=run_once('openai run frontend is not loading'); print(json.dumps({'ok': r.get('ok'), 'suggested': r.get('local_validation', {}).get('intent'), 'executed': r.get('executed_suggested_intent'), 'execution_type': (r.get('execution_result') or {}).get('execution_type')}, indent=2)); raise SystemExit(0 if r.get('executed_suggested_intent') is True else 1)"
}

Write-Host ""
Write-Host "========================================"
if ($Failures -eq 0) {
    Write-Host "[OK] Phase 3.5 safe execution test completed."
    Write-Host "OpenAI can route, but local Vetri performs safety validation before read-only execution."
} else {
    Write-Host "[FAIL] Phase 3.5 smoke test completed with $Failures failure(s)."
}
Write-Host "========================================"

exit $Failures
