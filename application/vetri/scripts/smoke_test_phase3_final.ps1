$Root = "Z:\HomeLLM"
Set-Location $Root

Write-Host "========================================"
Write-Host " Vetri AI Phase 3 Final Smoke Test"
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

function Test-VetriCommandKey {
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

function Test-VetriNoExecution {
    param(
        [string]$CommandText
    )

    $env:VETRI_TEST_COMMAND = $CommandText

    python -c "import os, sys; from vetri_ai.main import run_once; cmd=os.environ['VETRI_TEST_COMMAND']; r=run_once(cmd); print(r.get('message')); print('executed=', r.get('executed_suggested_intent')); sys.exit(0 if r.get('executed_suggested_intent') is False else 1)"

    Remove-Item Env:\VETRI_TEST_COMMAND -ErrorAction SilentlyContinue
}

function Test-VetriExecution {
    param(
        [string]$CommandText
    )

    $env:VETRI_TEST_COMMAND = $CommandText

    python -c "import os, sys; from vetri_ai.main import run_once; cmd=os.environ['VETRI_TEST_COMMAND']; r=run_once(cmd); print(r.get('message')); print('executed=', r.get('executed_suggested_intent')); print('execution_result=', bool(r.get('execution_result'))); sys.exit(0 if r.get('executed_suggested_intent') is True and r.get('execution_result') else 1)"

    Remove-Item Env:\VETRI_TEST_COMMAND -ErrorAction SilentlyContinue
}

Run-Test "Python syntax - main.py" {
    python -m py_compile Z:\HomeLLM\vetri_ai\main.py
}

Run-Test "Python syntax - settings.py" {
    python -m py_compile Z:\HomeLLM\vetri_ai\settings.py
}

Run-Test "Python syntax - intent_router.py" {
    python -m py_compile Z:\HomeLLM\vetri_ai\routing\intent_router.py
}

Run-Test "Python syntax - safety_router.py" {
    python -m py_compile Z:\HomeLLM\vetri_ai\safety\safety_router.py
}

Run-Test "Python syntax - policy_engine.py" {
    python -m py_compile Z:\HomeLLM\vetri_ai\safety\policy_engine.py
}

Run-Test "Python syntax - backend_client.py" {
    python -m py_compile Z:\HomeLLM\vetri_ai\clients\backend_client.py
}

Run-Test "Python syntax - ssh_bridge_client.py" {
    python -m py_compile Z:\HomeLLM\vetri_ai\clients\ssh_bridge_client.py
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

Run-Test "Python syntax - context_packet.py" {
    python -m py_compile Z:\HomeLLM\vetri_ai\ai\context_packet.py
}

Run-Test "Python syntax - prompt_builder.py" {
    python -m py_compile Z:\HomeLLM\vetri_ai\ai\prompt_builder.py
}

Run-Test "Python syntax - openai_client.py" {
    python -m py_compile Z:\HomeLLM\vetri_ai\ai\openai_client.py
}

Run-Test "Python syntax - formatters.py" {
    python -m py_compile Z:\HomeLLM\vetri_ai\utils\formatters.py
}

Run-Test "Settings check" {
    python -c "from vetri_ai.settings import get_settings; s=get_settings(); print({'openai_enabled': s.openai_enabled, 'model': s.openai_model, 'backend_url': s.backend_url})"
}

Run-Test "SSH alias vetri-mac" {
    ssh vetri-mac "hostname; whoami; pwd"
}

Run-Test "Endpoint validation" {
    python -c "from vetri_ai.main import run_once; import sys; r=run_once('validate endpoints'); print(r.get('message')); sys.exit(0 if r.get('ok') else 1)"
}

Run-Test "Skill validation" {
    python -c "from vetri_ai.main import run_once; import sys; r=run_once('validate skills'); print(r.get('message')); sys.exit(0 if r.get('ok') else 1)"
}

Run-Test "Phase 2 diagnosis still works" {
    Test-VetriCommandKey -CommandText "diagnose immich" -ExpectedKey "diagnosis"
}

Run-Test "Natural diagnosis phrase still works" {
    Test-VetriCommandKey -CommandText "why is immich slow" -ExpectedKey "diagnosis"
}

Run-Test "Context preview still works" {
    Test-VetriCommandKey -CommandText "preview context immich" -ExpectedKey "context_packet"
}

Run-Test "Context packet redaction check" {
    python -c "from vetri_ai.main import run_once; import json, sys; r=run_once('preview context immich'); text=json.dumps(r).lower(); bad=['raw_result','api_key','password','token','secret','ssh_key']; found=[x for x in bad if x in text]; print('found=', found); sys.exit(0 if not found else 1)"
}

Run-Test "OpenAI explanation works" {
    Test-VetriCommandKey -CommandText "explain diagnose immich" -ExpectedKey "openai_explanation"
}

Run-Test "OpenAI suggestion mode does not execute" {
    Test-VetriNoExecution -CommandText "openai intent why is immich slow"
}

Run-Test "OpenAI-assisted read-only execution works" {
    Test-VetriExecution -CommandText "openai run why is immich slow"
}

Run-Test "OpenAI-assisted backup execution works" {
    Test-VetriExecution -CommandText "openai run backup looks wrong"
}

Run-Test "OpenAI-assisted frontend execution works" {
    Test-VetriExecution -CommandText "openai run frontend is not loading"
}

Run-Test "JSON boundary for safe execution" {
    python -c "from vetri_ai.main import run_once; import json, sys; r=run_once('openai run tailscale is not working'); print(json.dumps({'ok': r.get('ok'), 'suggested': r.get('local_validation', {}).get('intent'), 'valid': r.get('local_validation', {}).get('valid'), 'executed': r.get('executed_suggested_intent'), 'execution_type': (r.get('execution_result') or {}).get('execution_type')}, indent=2)); sys.exit(0 if r.get('executed_suggested_intent') is True else 1)"
}

Write-Host ""
Write-Host "========================================"
if ($Failures -eq 0) {
    Write-Host "[OK] Phase 3 final smoke test passed."
    Write-Host "Phase 3 is ready to close."
} else {
    Write-Host "[FAIL] Phase 3 final smoke test completed with $Failures failure(s)."
}
Write-Host "========================================"

exit $Failures
