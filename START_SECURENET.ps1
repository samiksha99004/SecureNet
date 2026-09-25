# Start SecureNet: FastAPI backend (port 8000) + Vite dev server (port 5173), then open the browser.
# Each server runs in its own window; close those windows to stop SecureNet.
# Run as Administrator for live packet capture (needs Npcap) and Protection-mode firewall blocking.
# First time on a PC: run SETUP.bat.

$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'scripts\securenet-env.ps1')

function Fail($text) { Write-Host "`n$text" -ForegroundColor Red; exit 1 }
function Test-Port($port) { [bool](Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) }

if (-not (Test-Path (Join-Path $BackendDir '.env'))) {
    Fail 'backend\.env is missing - copy it from the original computer, then run SETUP.bat.'
}
if (-not (Test-SecureNetVenv)) { Fail 'The Python environment is missing or was copied from another PC - run SETUP.bat first.' }
$nodeDir = Find-SecureNetNode
if (-not $nodeDir) { Fail 'Node.js 22+ was not found - run SETUP.bat first.' }
if (-not (Test-SecureNetFrontendDeps)) { Fail 'Frontend packages are not installed - run SETUP.bat first.' }

$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host 'Note: not running as Administrator - live capture / blocking will be unavailable.' -ForegroundColor Yellow
}

# Child windows inherit this environment (Node on PATH, caches off C:)
Use-SecureNetCaches
$env:Path = "$nodeDir;$env:Path"

if (Test-Port 8000) {
    Write-Host 'Backend already running on port 8000.'
} else {
    Write-Host 'Starting backend on http://127.0.0.1:8000 ...' -ForegroundColor Cyan
    Start-Process cmd.exe -WorkingDirectory $BackendDir -ArgumentList '/k', `
        'title SecureNet Backend & venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000'
}
if (Test-Port 5173) {
    Write-Host 'Frontend already running on port 5173.'
} else {
    Write-Host 'Starting frontend on http://localhost:5173 ...' -ForegroundColor Cyan
    Start-Process cmd.exe -WorkingDirectory $FrontendDir -ArgumentList '/k', 'title SecureNet Frontend & npm run dev'
}

Write-Host 'Waiting for SecureNet to come up...'
$deadline = (Get-Date).AddSeconds(90)
$ready = $false
while ((Get-Date) -lt $deadline) {
    try {
        Invoke-WebRequest 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 3 | Out-Null
        Invoke-WebRequest 'http://localhost:5173' -UseBasicParsing -TimeoutSec 3 | Out-Null
        $ready = $true; break
    } catch { Start-Sleep -Milliseconds 700 }
}
if (-not $ready) {
    Fail 'SecureNet did not start within 90 seconds - check the "SecureNet Backend" and "SecureNet Frontend" windows for the error.'
}
Start-Process 'http://localhost:5173'
Write-Host 'SecureNet is running. Keep the two server windows open; close them to stop SecureNet.' -ForegroundColor Green
