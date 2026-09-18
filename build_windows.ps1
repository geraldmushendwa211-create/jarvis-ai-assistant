$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root
$python = Join-Path $root "venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Project environment not found. Create venv first, then run this script again."
}

Write-Host "Installing/updating PyInstaller in the active environment..."
& $python -m pip install pyinstaller

Write-Host "Building the native Jarvis desktop application..."
& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --name Jarvis `
    --console `
    --add-data "web;web" `
    --collect-submodules skills `
    brain/main.py

Write-Host "Build complete: dist\Jarvis\Jarvis.exe"
Write-Host "Copy your .env file beside Jarvis.exe before launching it."