$ErrorActionPreference = "Stop"
$Root = "Z:\HomeLLM"
$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$Target = Join-Path $Root "data\manual_backup_$Stamp"
New-Item -ItemType Directory -Force $Target | Out-Null
Copy-Item -Path (Join-Path $Root "config") -Destination $Target -Recurse -Force
Copy-Item -Path (Join-Path $Root "data\project_memory") -Destination $Target -Recurse -Force
Copy-Item -Path (Join-Path $Root "data\personal_memory") -Destination $Target -Recurse -Force
Write-Host "Backup scaffold copied config and memory to $Target"
