$Root = "Z:\HomeLLM"
Set-Location $Root

Write-Host "========================================"
Write-Host " Vetri AI Phase 3.1 OpenAI Skeleton Test"
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

Run-Test "Python syntax - settings.py" {
    python -m py_compile Z:\HomeLLM\vetri_ai\settings.py
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

Run-Test "Settings OpenAI fields load" {
    python -c "from vetri_ai.settings import get_settings; s=get_settings(); print({'openai_enabled': s.openai_enabled, 'openai_model': s.openai_model})"
}

Run-Test "Context packet builder" {
    python -c "from vetri_ai.ai.context_packet import ContextPacketBuilder; p=ContextPacketBuilder().build_from_result('diagnosis_explanation','test',{'ok':True,'raw_result':{'secret':'bad'}},['diagnose_immich']); print(p)"
}

Run-Test "Prompt builder" {
    python -c "from vetri_ai.ai.context_packet import ContextPacketBuilder; from vetri_ai.ai.prompt_builder import PromptBuilder; p=ContextPacketBuilder().build_from_result('diagnosis_explanation','test',{'ok':True},['diagnose_immich']); prompt=PromptBuilder().build_explanation_prompt(p); print(prompt[:500])"
}

Run-Test "OpenAI client disabled by default" {
    python -c "from vetri_ai.settings import get_settings; from vetri_ai.ai.openai_client import OpenAIClient; s=get_settings(); c=OpenAIClient(s.openai_enabled,s.openai_api_key,s.openai_model); r=c.explain('test'); print(r); raise SystemExit(0 if r.get('status') in ['disabled','not_configured'] else 1)"
}

Write-Host ""
Write-Host "========================================"
if ($Failures -eq 0) {
    Write-Host "[OK] Phase 3.1 OpenAI skeleton test passed."
    Write-Host "OpenAI foundation is ready, but still disabled by default."
} else {
    Write-Host "[FAIL] Phase 3.1 smoke test completed with $Failures failure(s)."
}
Write-Host "========================================"

exit $Failures
