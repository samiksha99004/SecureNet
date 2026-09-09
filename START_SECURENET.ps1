# SecureNet Complete System Startup Script
# Run this as Administrator for full functionality

Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  SecureNet IDS - Complete System Startup" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "⚠️  WARNING: Not running as Administrator" -ForegroundColor Yellow
    Write-Host "   Packet capture requires administrator privileges." -ForegroundColor Yellow
    Write-Host "   Right-click PowerShell and 'Run as Administrator'" -ForegroundColor Yellow
    Write-Host ""
    $response = Read-Host "Continue anyway? (y/n)"
    if ($response -ne 'y') {
        exit 1
    }
}

# Check PostgreSQL
Write-Host "[1/5] Checking PostgreSQL..." -ForegroundColor Yellow
$pgService = Get-Service -Name "postgresql*" -ErrorAction SilentlyContinue
if ($pgService -and $pgService.Status -eq 'Running') {
    Write-Host "✓ PostgreSQL is running" -ForegroundColor Green
} else {
    Write-Host "✗ PostgreSQL not running" -ForegroundColor Red
    Write-Host "  Please start PostgreSQL service first" -ForegroundColor Gray
    exit 1
}

# Check Python environment
Write-Host ""
Write-Host "[2/5] Checking Python environment..." -ForegroundColor Yellow
if (Test-Path "backend\venv\Scripts\python.exe") {
    Write-Host "✓ Virtual environment found" -ForegroundColor Green
} else {
    Write-Host "✗ Virtual environment not found" -ForegroundColor Red
    Write-Host "  Run backend\setup.ps1 first" -ForegroundColor Gray
    exit 1
}

# Check ML models
Write-Host ""
Write-Host "[3/5] Checking ML models..." -ForegroundColor Yellow
$mlDir = "F:\all_10_csv_manual"
$requiredFiles = @(
    "isolation_forest_model.pkl",
    "xgboost_hybrid_model.pkl",
    "xgboost_multiclass_model.pkl",
    "label_encoder.pkl",
    "feature_columns.pkl"
)

$allFound = $true
foreach ($file in $requiredFiles) {
    $path = Join-Path $mlDir $file
    if (Test-Path $path) {
        Write-Host "  ✓ $file" -ForegroundColor Green
    } else {
        Write-Host "  ✗ $file" -ForegroundColor Red
        $allFound = $false
    }
}

if (-not $allFound) {
    Write-Host "✗ Some ML models are missing" -ForegroundColor Red
    exit 1
}

# Start Backend
Write-Host ""
Write-Host "[4/5] Starting Backend..." -ForegroundColor Yellow
Write-Host "  Backend URL: http://localhost:8000" -ForegroundColor Gray
Write-Host "  API Docs: http://localhost:8000/api/docs" -ForegroundColor Gray

$backendJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    Set-Location backend
    & ".\venv\Scripts\Activate.ps1"
    & ".\venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
}

# Wait for backend to start
Write-Host "  Waiting for backend to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# Check if backend is running
try {
    $response = Invoke-WebRequest -Uri "http://localhost:8000/health" -UseBasicParsing -TimeoutSec 5
    Write-Host "✓ Backend started successfully" -ForegroundColor Green
} catch {
    Write-Host "✗ Backend failed to start" -ForegroundColor Red
    Stop-Job $backendJob
    Remove-Job $backendJob
    exit 1
}

# Start Frontend
Write-Host ""
Write-Host "[5/5] Starting Frontend..." -ForegroundColor Yellow
Write-Host "  Frontend URL: http://localhost:5173" -ForegroundColor Gray

$frontendJob = Start-Job -ScriptBlock {
    Set-Location $using:PWD
    Set-Location "SecureNet (2)\SecureNet\frontend"
    npm run dev
}

# Wait for frontend to start
Write-Host "  Waiting for frontend to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 8

Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  SecureNet System Running" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend:  http://localhost:8000" -ForegroundColor White
Write-Host "Frontend: http://localhost:5173" -ForegroundColor White
Write-Host "API Docs: http://localhost:8000/api/docs" -ForegroundColor White
Write-Host ""
Write-Host "Press Ctrl+C to stop all services" -ForegroundColor Yellow
Write-Host ""

# Keep running and show logs
try {
    while ($true) {
        Start-Sleep -Seconds 1
    }
} finally {
    Write-Host ""
    Write-Host "Stopping services..." -ForegroundColor Yellow
    Stop-Job $backendJob -ErrorAction SilentlyContinue
    Remove-Job $backendJob -ErrorAction SilentlyContinue
    Stop-Job $frontendJob -ErrorAction SilentlyContinue
    Remove-Job $frontendJob -ErrorAction SilentlyContinue
    Write-Host "✓ All services stopped" -ForegroundColor Green
}
