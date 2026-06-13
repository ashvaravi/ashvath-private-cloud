$Root = "Z:\HomeLLM"
Set-Location $Root

Write-Host "========================================"
Write-Host " Vetri AI Phase 2 Final Smoke Test"
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

function Test-VetriCommand {
    param(
        [string]$CommandText,
        [string]$ExpectedKey
    )

    $env:VETRI_TEST_COMMAND = $CommandText
    $env:VETRI_EXPECTED_KEY = $ExpectedKey

    python -c "import os, sys; from vetri_ai.main import run_once; cmd=os.environ['VETRI_TEST_COMMAND']; key=os.environ['VETRI_EXPECTED_KEY']; r=run_once(cmd); print(r.get('intent'), r.get('ok'), r.get('message')); sys.exit(0 if key in r else 1)"

    Remove-Item Env:\VETRI_TEST_COMMAND -ErrorAction SilentlyContinue
    Remove-Item Env:\VETRI_EXPECTED_KEY -ErrorAction SilentlyContinue
}

Run-Test "Python syntax - main.py" {
    python -m py_compile Z:\HomeLLM\vetri_ai\main.py
}

Run-Test "Python syntax - intent_router.py" {
    python -m py_compile Z:\HomeLLM\vetri_ai\routing\intent_router.py
}

Run-Test "Python syntax - safety_router.py" {
    python -m py_compile Z:\HomeLLM\vetri_ai\safety\safety_router.py
}

Run-Test "Python syntax - skill_runner.py" {
    python -m py_compile Z:\HomeLLM\vetri_ai\skills\skill_runner.py
}

Run-Test "Python syntax - skill_validator.py" {
    python -m py_compile Z:\HomeLLM\vetri_ai\skills\skill_validator.py
}

Run-Test "Python syntax - diagnosis_interpreter.py" {
    python -m py_compile Z:\HomeLLM\vetri_ai\skills\diagnosis_interpreter.py
}

Run-Test "Python syntax - formatters.py" {
    python -m py_compile Z:\HomeLLM\vetri_ai\utils\formatters.py
}

Run-Test "SSH alias vetri-mac" {
    ssh vetri-mac "hostname; whoami; pwd"
}

Run-Test "Python import check" {
    python -c "from vetri_ai.main import run_once; from vetri_ai.utils.formatters import format_human_result; print('imports ok')"
}

Run-Test "Endpoint validation" {
    python -c "from vetri_ai.main import run_once; import sys; r=run_once('validate endpoints'); print(r.get('message')); sys.exit(0 if r.get('ok') else 1)"
}

Run-Test "Skill validation" {
    python -c "from vetri_ai.main import run_once; import sys; r=run_once('validate skills'); print(r.get('message')); sys.exit(0 if r.get('ok') else 1)"
}

$DirectDiagnosisCommands = @(
    "diagnose immich",
    "diagnose backup",
    "diagnose storage",
    "diagnose network",
    "diagnose backend",
    "diagnose frontend"
)

foreach ($CommandText in $DirectDiagnosisCommands) {
    Run-Test "Direct diagnosis: $CommandText" {
        Test-VetriCommand -CommandText $CommandText -ExpectedKey "diagnosis"
    }
}

$NaturalPhrases = @(
    "why is immich slow",
    "backup looks wrong",
    "is my ssd having issues",
    "tailscale is not working",
    "backend seems down",
    "frontend is not loading"
)

foreach ($Phrase in $NaturalPhrases) {
    Run-Test "Natural phrase: $Phrase" {
        Test-VetriCommand -CommandText $Phrase -ExpectedKey "diagnosis"
    }
}

Run-Test "JSON debug diagnosis" {
    python -c "from vetri_ai.main import run_once; import json; r=run_once('diagnose immich'); print(json.dumps({'intent': r.get('intent'), 'ok': r.get('ok'), 'has_diagnosis': 'diagnosis' in r}, indent=2)); raise SystemExit(0 if 'diagnosis' in r else 1)"
}

Write-Host ""
Write-Host "========================================"
if ($Failures -eq 0) {
    Write-Host "[OK] Phase 2 final smoke test passed."
    Write-Host "Phase 2 is ready to close."
} else {
    Write-Host "[FAIL] Phase 2 final smoke test completed with $Failures failure(s)."
}
Write-Host "========================================"

exit $Failures
