$ErrorActionPreference = "Continue"
$Root = "Z:\HomeLLM"
$LocalTarget = Join-Path $Root "data\raw_imports\mac_exports"
$LogPath = Join-Path $Root "logs\sync_jobs.jsonl"
$RemoteFolder = "~/Ashvath-private-cloud/exports/for-vetri-ai/"
$Expected = @(
  "latest_status_snapshot.json",
  "latest_backup_summary.json",
  "latest_dashboard_summary.json",
  "latest_backend_health.json",
  "latest_homeassistant_summary.json",
  "latest_network_summary.json",
  "latest_service_summary.json",
  "sanitized_events.jsonl",
  "export_manifest.json"
)

New-Item -ItemType Directory -Force $LocalTarget | Out-Null
New-Item -ItemType Directory -Force (Split-Path $LogPath) | Out-Null

function Write-SyncLog($Status, $Message) {
  $Entry = [ordered]@{
    timestamp = (Get-Date).ToString("o")
    status = $Status
    message = $Message
    local_target = $LocalTarget
  } | ConvertTo-Json -Compress
  Add-Content -Path $LogPath -Value $Entry -Encoding UTF8
}

ssh vetri-mac "~/Ashvath-private-cloud/scripts/export-vetri-summary.sh"
if ($LASTEXITCODE -ne 0) {
  Write-SyncLog "warning" "Mac export summary script failed or Mac unreachable. Continuing local AI brain operation."
  Write-Warning "Mac unreachable or export script failed. Local AI brain can continue."
  exit 0
}

foreach ($File in $Expected) {
  scp "vetri-mac:$RemoteFolder$File" $LocalTarget
  if ($LASTEXITCODE -ne 0) {
    Write-SyncLog "warning" "Failed to copy $File"
  }
}

$Manifest = Join-Path $LocalTarget "export_manifest.json"
if (Test-Path $Manifest) {
  Write-SyncLog "success" "Mac exports synced and manifest is present."
  Write-Host "Mac exports synced to $LocalTarget"
} else {
  Write-SyncLog "warning" "Sync completed but export_manifest.json is missing."
  Write-Warning "export_manifest.json missing after sync."
}
