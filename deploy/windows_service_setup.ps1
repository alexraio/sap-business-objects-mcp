<#
.SYNOPSIS
    Registers the SAP BusinessObjects MCP Server (bo-mcp) as a native Windows Service.
.DESCRIPTION
    Configures bo-mcp to run natively on a Windows Server hosting SAP BusinessObjects BI 4.3 SP5,
    leveraging the host's Windows ODBC System DSN (for Auditing DB) and local logging directory.
#>

param(
    [string]$ServiceName = "SAPBusinessObjectsMCP",
    [string]$InstallDir = "C:\bo-mcp",
    [string]$UvPath = "C:\Users\Administrator\.local\bin\uv.exe",
    [string]$BindHost = "0.0.0.0",
    [int]$BindPort = 8000,
    [string]$Transport = "streamable-http"
)

$ErrorActionPreference = "Stop"

Write-Host "Configuring Windows Service '$ServiceName' in '$InstallDir'..." -ForegroundColor Cyan

if (-not (Test-Path $InstallDir)) {
    throw "InstallDir '$InstallDir' does not exist."
}

# If NSSM (Non-Sucking Service Manager) is available on PATH, prefer it for clean stdout/stderr rotation
$nssm = Get-Command nssm.exe -ErrorAction SilentlyContinue
if ($null -ne $nssm) {
    & nssm install $ServiceName $UvPath "--directory" $InstallDir "run" "python" "server.py" "--transport" $Transport "--host" $BindHost "--port" "$BindPort"
    & nssm set $ServiceName AppDirectory $InstallDir
    & nssm set $ServiceName Description "SAP BusinessObjects 4.3 SP5 Remote MCP Server (Streamable HTTP / SSE)"
    & nssm set $ServiceName Start SERVICE_AUTO_START
    & nssm start $ServiceName
    Write-Host "Service '$ServiceName' installed and started via NSSM." -ForegroundColor Green
} else {
    $binPath = "`"$UvPath`" --directory `"$InstallDir`" run python server.py --transport $Transport --host $BindHost --port $BindPort"
    sc.exe create $ServiceName binPath= $binPath start= auto DisplayName= "SAP BusinessObjects MCP Server"
    sc.exe description $ServiceName "SAP BusinessObjects 4.3 SP5 Remote MCP Server (Streamable HTTP / SSE)"
    sc.exe failure $ServiceName reset= 86400 actions= restart/5000/restart/5000/restart/5000
    Write-Host "Service '$ServiceName' registered via sc.exe. Note: For production Windows deployments, NSSM is recommended." -ForegroundColor Yellow
}
