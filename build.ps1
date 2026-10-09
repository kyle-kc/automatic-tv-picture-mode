# Build script for automatic-tv-picture-mode
# This script prepares the environment and builds the executable using PyInstaller.

$ErrorActionPreference = "Stop"

$PythonExec = "C:\Users\kylek\AppData\Local\Programs\Python\Python313\python.exe"
$ProjectDir = "C:\Users\kylek\Source\automatic-tv-picture-mode"
$BuildDir = Join-Path $ProjectDir "build"
$DistDir = Join-Path $ProjectDir "dist"

Write-Host "--- Starting Build Process ---" -ForegroundColor Cyan

# 1. Clean up previous builds
if (Test-Path $BuildDir) { Remove-Item -Recurse -Force $BuildDir }
if (Test-Path $DistDir) { Remove-Item -Recurse -Force $DistDir }
Write-Host "Cleaned old build and dist directories."

# 2. Install / Update dependencies
Write-Host "Installing dependencies from requirements.txt..." -ForegroundColor Yellow
& $PythonExec -m pip install --upgrade pip
& $PythonExec -m pip install -r $ProjectDir\requirements.txt

# 3. Run PyInstaller
# We use the main.spec file which already contains your configurations.
Write-Host "Running PyInstaller with main.spec..." -ForegroundColor Yellow
Push-Location $ProjectDir
& $PythonExec -m PyInstaller main.spec
Pop-Location

if ($LASTEXITCODE -eq 0) {
    Write-Host "--- Build Successful! ---" -ForegroundColor Green
    Write-Host "Executable located in: $DistDir"
} else {
    Write-Host "--- Build Failed ---" -ForegroundColor Red
    exit 1
}
