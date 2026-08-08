param(
  [string]$Version = "0.4.6.1"
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
py -m pip install --upgrade pip
py -m pip install -e ".[build,test]"
py -m pytest -q
py -m compileall -q tiny_rogues_tracker scripts tests
py -m PyInstaller --noconfirm --windowed --onefile --name "TinyRoguesTracker-v0.4.6.1" --add-data "ids.json;." --add-data "tiny_rogues_tracker\assets;tiny_rogues_tracker\assets" scripts\run_gui.py
Write-Host "Built dist\TinyRoguesTracker-v0.4.6.1.exe"
