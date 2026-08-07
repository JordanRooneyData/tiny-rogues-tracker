param([string]$Repo = "JordanRooneyData/tiny-rogues-tracker")
$ErrorActionPreference = "Stop"
$installRoot = Join-Path $env:LOCALAPPDATA "TinyRoguesTracker"
New-Item -ItemType Directory -Force -Path $installRoot | Out-Null
$api = "https://api.github.com/repos/$Repo/releases/latest"
$release = Invoke-RestMethod -Uri $api -Headers @{"User-Agent"="TinyRoguesTrackerBootstrap"}
$asset = $release.assets | Where-Object { $_.name -match "TinyRoguesTracker-v.*-Setup\.exe$" } | Select-Object -First 1
if (-not $asset) { $asset = $release.assets | Where-Object { $_.name -match "Setup\.exe$|installer.*\.exe$" } | Select-Object -First 1 }
if (-not $asset) { throw "No Windows installer asset found on latest release." }
$target = Join-Path $env:TEMP $asset.name
Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $target
if ((Get-Item $target).Length -le 0) { throw "Downloaded installer is empty." }
Start-Process -FilePath $target -Wait
