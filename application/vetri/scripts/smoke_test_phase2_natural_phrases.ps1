$Root = "Z:\HomeLLM"
Set-Location $Root

Write-Host "========================================"
Write-Host " Vetri AI Phase 2.5 Natural Diagnosis Phrase Test"
Write-Host "========================================"

$Phrases = @(
    "why is immich slow",
    "immich is not opening",
    "photo backup not working",
    "backup looks wrong",
    "why are backups failing",
    "cloud backup problem",
    "is my ssd having issues",
    "external ssd not mounted",
    "storage problem",
    "tailscale is not working",
    "remote access not working",
    "mac not reachable",
    "backend seems down",
    "api not working",
    "backend unreachable",
    "frontend is not loading",
    "ui not opening",
    "vetri app not working"
)

foreach ($Phrase in $Phrases) {
    Write-Host ""
    Write-Host "---- $Phrase ----"
    python -c "from vetri_ai.main import run_once; import json; r=run_once('$Phrase'); print(json.dumps({'input':'$Phrase','ok':r.get('ok'),'intent':r.get('intent'),'confidence':r.get('confidence'),'message':r.get('message')}, indent=2))"
}

Write-Host ""
Write-Host "Phase 2.5 natural diagnosis phrase test completed."
