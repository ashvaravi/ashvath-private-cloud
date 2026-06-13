$Root = "Z:\HomeLLM"
Set-Location $Root

Write-Host "========================================"
Write-Host " Vetri AI Phase 3.4 Intent Suggestion Test"
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

Run-Test "Python syntax - prompt_builder.py" {
    python -m py_compile Z:\HomeLLM\vetri_ai\ai\prompt_builder.py
}

Run-Test "OpenAI intent suggestion - immich" {
    python -c "from vetri_ai.main import run_once; r=run_once('openai intent why is immich slow'); print(r.get('message')); raise SystemExit(0 if 'openai_intent_suggestion' in r and r.get('executed_suggested_intent') is False else 1)"
}

Run-Test "OpenAI intent suggestion - frontend" {
    python -c "from vetri_ai.main import run_once; r=run_once('suggest intent for frontend is not loading'); print(r.get('message')); raise SystemExit(0 if 'openai_intent_suggestion' in r and r.get('executed_suggested_intent') is False else 1)"
}

Run-Test "OpenAI intent suggestion JSON boundary" {
    python -c "from vetri_ai.main import run_once; import json; r=run_once('ai route backup looks wrong'); print(json.dumps({'ok': r.get('ok'), 'suggested': r.get('local_validation', {}).get('intent'), 'executed': r.get('executed_suggested_intent')}, indent=2)); raise SystemExit(0 if r.get('executed_suggested_intent') is False else 1)"
}

Write-Host ""
Write-Host "========================================"
if ($Failures -eq 0) {
    Write-Host "[OK] Phase 3.4 intent suggestion test completed."
    Write-Host "OpenAI can suggest intents, but Vetri does not execute them yet."
} else {
    Write-Host "[FAIL] Phase 3.4 smoke test completed with $Failures failure(s)."
}
Write-Host "========================================"

exit $Failures
