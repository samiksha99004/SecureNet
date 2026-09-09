# SecureNet Backend Setup Script for Windows/PowerShell

Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  SecureNet Backend Setup" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Check Python version
Write-Host "[1/7] Checking Python version..." -ForegroundColor Yellow
$pythonVersion = python --version 2>&1
if ($pythonVersion -match "Python 3\.([0-9]+)") {
    $minorVersion = [int]$matches[1]
    if ($minorVersion -ge 10) {
        Write-Host "✓ Python version OK: $pythonVersion" -ForegroundColor Green
    } else {
        Write-Host "✗ Python 3.10+ required. Found: $pythonVersion" -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "✗ Python not found or version check failed" -ForegroundColor Red
    exit 1
}

# Create virtual environment
Write-Host ""
Write-Host "[2/7] Creating virtual environment..." -ForegroundColor Yellow
if (Test-Path "venv") {
    Write-Host "  Virtual environment already exists, skipping..." -ForegroundColor Gray
} else {
    python -m venv venv
    Write-Host "✓ Virtual environment created" -ForegroundColor Green
}

# Activate virtual environment
Write-Host ""
Write-Host "[3/7] Activating virtual environment..." -ForegroundColor Yellow
& ".\venv\Scripts\Activate.ps1"
Write-Host "✓ Virtual environment activated" -ForegroundColor Green

# Install dependencies
Write-Host ""
Write-Host "[4/7] Installing Python dependencies..." -ForegroundColor Yellow
pip install --upgrade pip | Out-Null
pip install -r requirements.txt
Write-Host "✓ Dependencies installed" -ForegroundColor Green

# Create .env file if it doesn't exist
Write-Host ""
Write-Host "[5/7] Setting up environment configuration..." -ForegroundColor Yellow
if (Test-Path ".env") {
    Write-Host "  .env file already exists, skipping..." -ForegroundColor Gray
} else {
    Copy-Item ".env.example" ".env"
    Write-Host "✓ Created .env from template" -ForegroundColor Green
    Write-Host "  ⚠  Please edit .env with your configuration!" -ForegroundColor Yellow
}

# Create directories
Write-Host ""
Write-Host "[6/7] Creating application directories..." -ForegroundColor Yellow
$directories = @("logs", "models", "reports")
foreach ($dir in $directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  Created: $dir/" -ForegroundColor Gray
    }
}
Write-Host "✓ Directories created" -ForegroundColor Green

# Check PostgreSQL
Write-Host ""
Write-Host "[7/7] Checking PostgreSQL..." -ForegroundColor Yellow
try {
    $pgVersion = psql --version 2>&1
    Write-Host "✓ PostgreSQL found: $pgVersion" -ForegroundColor Green
} catch {
    Write-Host "⚠  PostgreSQL not found in PATH" -ForegroundColor Yellow
    Write-Host "  Please install PostgreSQL from: https://www.postgresql.org/download/windows/" -ForegroundColor Gray
}

# Final instructions
Write-Host ""
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "  Setup Complete!" -ForegroundColor Cyan
Write-Host "════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host ""
Write-Host "  1. Edit .env file with your configuration" -ForegroundColor Gray
Write-Host "     - Set DATABASE_URL" -ForegroundColor Gray
Write-Host "     - Set JWT_SECRET (min 32 characters)" -ForegroundColor Gray
Write-Host "     - Set CORS_ORIGINS to your frontend URL" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Create PostgreSQL database:" -ForegroundColor Gray
Write-Host "     psql -U postgres" -ForegroundColor DarkGray
Write-Host "     CREATE DATABASE securenet;" -ForegroundColor DarkGray
Write-Host "     CREATE USER securenet WITH PASSWORD 'your_password';" -ForegroundColor DarkGray
Write-Host "     GRANT ALL PRIVILEGES ON DATABASE securenet TO securenet;" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  3. Run database migrations:" -ForegroundColor Gray
Write-Host "     alembic upgrade head" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  4. Start the development server:" -ForegroundColor Gray
Write-Host "     uvicorn app.main:app --reload" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  5. Access API documentation:" -ForegroundColor Gray
Write-Host "     http://localhost:8000/api/docs" -ForegroundColor DarkGray
Write-Host ""
Write-Host "For more information, see README.md" -ForegroundColor White
Write-Host ""
