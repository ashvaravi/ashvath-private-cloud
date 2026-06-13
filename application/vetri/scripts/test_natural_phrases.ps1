$Root = "Z:\HomeLLM"
Set-Location $Root

Write-Host "========================================"
Write-Host " Vetri AI Phase 1B.6 Natural Phrase Test"
Write-Host "========================================"

$Phrases = @(
    "what is the state of the cloud backup",
    "how are my backups",
    "is my SSD mounted",
    "how is my private cloud",
    "are all services online",
    "is tailscale working",
    "can you reach the mac",
    "what phase are we in"
)

foreach ($Phrase in $Phrases) {
    Write-Host ""
    Write-Host "---- $Phrase ----"
    python -c "from vetri_ai.main import run_once; import json; r=run_once('$Phrase'); print(json.dumps({'input':'$Phrase','ok':r.get('ok'),'intent':r.get('intent'),'confidence':r.get('confidence'),'message':r.get('message')}, indent=2))"
}

Write-Host ""
Write-Host "Natural phrase test completed."
