$Root = "Z:\HomeLLM"
Set-Location $Root

Write-Host "========================================"
Write-Host " Vetri AI Phase 3.2 Context Packet Test"
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

function Test-ContextCommand {
    param(
        [string]$CommandText
    )

    $env:VETRI_TEST_COMMAND = $CommandText

    python -c "import os, sys; from vetri_ai.main import run_once; cmd=os.environ['VETRI_TEST_COMMAND']; r=run_once(cmd); print(r.get('intent'), r.get('ok'), 'context_packet' in r); sys.exit(0 if 'context_packet' in r else 1)"

    Remove-Item Env:\VETRI_TEST_COMMAND -ErrorAction SilentlyContinue
}

Run-Test "Python syntax - main.py" {
    python -m py_compile Z:\HomeLLM\vetri_ai\main.py
}

Run-Test "Python syntax - formatters.py" {
    python -m py_compile Z:\HomeLLM\vetri_ai\utils\formatters.py
}

Run-Test "Python syntax - context_packet.py" {
    python -m py_compile Z:\HomeLLM\vetri_ai\ai\context_packet.py
}

Run-Test "Context preview - immich" {
    Test-ContextCommand -CommandText "preview context immich"
}

Run-Test "Context preview - backup" {
    Test-ContextCommand -CommandText "preview context backup"
}

Run-Test "Context preview - storage" {
    Test-ContextCommand -CommandText "preview context storage"
}

Run-Test "Context preview - network" {
    Test-ContextCommand -CommandText "preview context network"
}

Run-Test "Context preview human format" {
    python -c "from vetri_ai.main import run_once; from vetri_ai.utils.formatters import format_human_result; print(format_human_result(run_once('preview context immich')))"
}

Run-Test "Context preview JSON check redaction" {
    python -c "from vetri_ai.main import run_once; import json; r=run_once('preview context immich'); text=json.dumps(r); print(text[:1000]); raise SystemExit(0 if 'raw_result' not in text.lower() else 1)"
}

Write-Host ""
Write-Host "========================================"
if ($Failures -eq 0) {
    Write-Host "[OK] Phase 3.2 context packet test passed."
    Write-Host "Sanitized context packet preview is ready."
} else {
    Write-Host "[FAIL] Phase 3.2 smoke test completed with $Failures failure(s)."
}
Write-Host "========================================"

exit $Failures
