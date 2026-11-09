<#
.SYNOPSIS
    Automated Setup & Verification Script for SAP BusinessObjects MCP Server on Windows.
.DESCRIPTION
    Ensures Astral 'uv' package manager is installed, synchronizes Python dependencies,
    provisions .env if missing, and executes the 4-subsystem self-diagnostic health check (server.py doctor).
#>

[CmdletBinding()]
param(
    [switch]$SkipDoctor = $false
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "=============================================================" -ForegroundColor Cyan
Write-Host "   SAP BusinessObjects 4.3 SP5 - bo-mcp Windows Setup" -ForegroundColor Cyan
Write-Host "=============================================================" -ForegroundColor Cyan
Write-Host "Project directory: $ProjectRoot" -ForegroundColor Gray

# Step 1: Ensure uv is installed
$UvCmd = Get-Command uv.exe -ErrorAction SilentlyContinue
if ($null -eq $UvCmd) {
    $UserUv = "$env:USERPROFILE\.local\bin\uv.exe"
    if (Test-Path $UserUv) {
        $env:Path = "$env:USERPROFILE\.local\bin;" + $env:Path
        $UvCmd = Get-Command uv.exe -ErrorAction SilentlyContinue
    }
}

if ($null -eq $UvCmd) {
    Write-Host "[INFO] 'uv' not found. Installing Astral uv in user profile..." -ForegroundColor Yellow
    Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    $env:Path = "$env:USERPROFILE\.local\bin;" + $env:Path
    $UvCmd = Get-Command uv.exe -ErrorAction SilentlyContinue
    if ($null -eq $UvCmd) {
        throw "Failed to install 'uv'. Please install manually from https://astral.sh/uv"
    }
}
Write-Host "[OK] Astral uv found: $(& uv --version)" -ForegroundColor Green

# Step 2: Sync dependencies
Write-Host "[INFO] Synchronizing virtual environment and dependencies via uv..." -ForegroundColor Cyan
Set-Location -Path $ProjectRoot
& uv sync
Write-Host "[OK] Dependencies synchronized." -ForegroundColor Green

# Step 3: Setup .env file
$EnvFile = Join-Path $ProjectRoot ".env"
$EnvExample = Join-Path $ProjectRoot ".env.example"

if (Test-Path $EnvFile) {
    Write-Host "[INFO] Existing .env file found." -ForegroundColor Gray
} else {
    if (Test-Path $EnvExample) {
        Write-Host "[WARN] Creating .env from .env.example..." -ForegroundColor Yellow
        Copy-Item -Path $EnvExample -Destination $EnvFile
        Write-Host "[OK] Created '$EnvFile'. Please update credentials as needed." -ForegroundColor Green
    }
}

# Step 4: Run doctor
if (-not $SkipDoctor) {
    Write-Host "`n[INFO] Running self-diagnostic health check (server.py doctor)...`n" -ForegroundColor Cyan
    & uv run python server.py doctor
    Write-Host "`n[OK] Doctor probe completed." -ForegroundColor Green
}

Write-Host "`n=============================================================" -ForegroundColor Green
Write-Host "   Setup & Verification Completed Successfully!" -ForegroundColor Green
Write-Host "=============================================================" -ForegroundColor Green
Write-Host "`nTo start in foreground mode for live testing:" -ForegroundColor White
Write-Host "  uv run python server.py --transport streamable-http --host 0.0.0.0 --port 8000" -ForegroundColor Cyan
Write-Host "`nTo register as a permanent Windows Service:" -ForegroundColor White
Write-Host "  powershell -ExecutionPolicy Bypass -File deploy\windows_service_setup.ps1`n" -ForegroundColor Cyan
