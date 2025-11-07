# ============================================================================
# AI-Assistant Docker Startup Script
# ============================================================================
# This script starts PostgreSQL and Redis services for development
# ============================================================================

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host "AI-ASSISTANT DOCKER STARTUP" -ForegroundColor Yellow
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
Write-Host "Checking Docker Desktop..." -ForegroundColor Cyan
try {
    docker ps | Out-Null
    Write-Host "✓ Docker Desktop is running" -ForegroundColor Green
} catch {
    Write-Host "✗ Docker Desktop is not running" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please start Docker Desktop and try again." -ForegroundColor Yellow
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 1
}

Write-Host ""

# Check if .env file exists
if (-not (Test-Path ".env")) {
    Write-Host "⚠  .env file not found!" -ForegroundColor Yellow
    Write-Host "Creating .env from .env.example..." -ForegroundColor Cyan
    Copy-Item .env.example .env
    Write-Host "✓ .env created" -ForegroundColor Green
    Write-Host ""
    Write-Host "⚠  Please edit .env file and update passwords before running again!" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Press any key to exit..."
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
    exit 0
}

Write-Host "Starting database services..." -ForegroundColor Cyan
Write-Host ""

# Start PostgreSQL and Redis
Write-Host "→ Starting PostgreSQL, Redis, and pgAdmin..." -ForegroundColor White
docker-compose up -d postgres redis pgadmin

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "✓ Services started successfully!" -ForegroundColor Green
    Write-Host ""
    
    # Wait for services to be healthy
    Write-Host "Waiting for services to be healthy..." -ForegroundColor Cyan
    Start-Sleep -Seconds 5
    
    # Check service status
    Write-Host ""
    Write-Host "Service Status:" -ForegroundColor Yellow
    docker-compose ps postgres redis pgadmin
    
    Write-Host ""
    Write-Host "=" -NoNewline -ForegroundColor Cyan
    Write-Host ("=" * 79) -ForegroundColor Cyan
    Write-Host "SERVICES READY" -ForegroundColor Green
    Write-Host "=" -NoNewline -ForegroundColor Cyan
    Write-Host ("=" * 79) -ForegroundColor Cyan
    Write-Host ""
    
    # Show access information
    Write-Host "Access Services:" -ForegroundColor Yellow
    Write-Host "  • PostgreSQL:  localhost:5432" -ForegroundColor White
    Write-Host "  • Redis:       localhost:6379" -ForegroundColor White
    Write-Host "  • pgAdmin:     http://localhost:5050" -ForegroundColor White
    Write-Host ""
    
    Write-Host "pgAdmin Login:" -ForegroundColor Yellow
    Write-Host "  • Email:    admin@aiassistant.local" -ForegroundColor White
    Write-Host "  • Password: admin123" -ForegroundColor White
    Write-Host ""
    
    Write-Host "Next Steps:" -ForegroundColor Yellow
    Write-Host "  1. Setup database: " -NoNewline -ForegroundColor White
    Write-Host "python database/scripts/setup_database.py" -ForegroundColor Cyan
    Write-Host "  2. Test connection: " -NoNewline -ForegroundColor White
    Write-Host "python database/utils/test_connection.py" -ForegroundColor Cyan
    Write-Host "  3. Start all services: " -NoNewline -ForegroundColor White
    Write-Host "docker-compose up -d" -ForegroundColor Cyan
    Write-Host ""
    
    Write-Host "View Logs:" -ForegroundColor Yellow
    Write-Host "  docker-compose logs -f postgres redis" -ForegroundColor Cyan
    Write-Host ""
    
} else {
    Write-Host ""
    Write-Host "✗ Failed to start services" -ForegroundColor Red
    Write-Host ""
    Write-Host "Check logs:" -ForegroundColor Yellow
    Write-Host "  docker-compose logs postgres redis pgadmin" -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 79) -ForegroundColor Cyan
Write-Host ""
