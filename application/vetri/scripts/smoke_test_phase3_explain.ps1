$Root = "Z:\HomeLLM"
Set-Location $Root

Write-Host "========================================"
Write-Host " Vetri AI Phase 3.3 OpenAI Explanation Test"
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

Run-Test "Python syntax - openai_client.py" {
    python -m py_compile Z:\HomeLLM\vetri_ai\ai\openai_client.py
}

Run-Test "Python syntax - formatters.py" {
    python -m py_compile Z:\HomeLLM\vetri_ai\utils\formatters.py
}

Run-Test "OpenAI settings check" {
    python -c "from vetri_ai.settings import get_settings; s=get_settings(); print({'enabled': s.openai_enabled, 'model': s.openai_model, 'has_key': bool(s.openai_api_key and s.openai_api_key != 'PASTE_OPENAI_API_KEY_HERE')})"
}

Run-Test "Explain diagnose immich" {
    python -c "from vetri_ai.main import run_once; from vetri_ai.utils.formatters import format_human_result; r=run_once('explain diagnose immich'); print(format_human_result(r)); raise SystemExit(0 if 'openai_explanation' in r else 1)"
}

Write-Host ""
Write-Host "========================================"
if ($Failures -eq 0) {
    Write-Host "[OK] Phase 3.3 OpenAI explanation test completed."
} else {
    Write-Host "[FAIL] Phase 3.3 smoke test completed with $Failures failure(s)."
}
Write-Host "========================================"

exit $Failures
