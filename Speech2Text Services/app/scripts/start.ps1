# 🎯 Vietnamese Speech-to-Text System
# Quick Launch Script

# Check Python environment
if (-not (Test-Path "s2t\Scripts\activate.bat")) {
    Write-Host "❌ Virtual environment not found at s2t\Scripts\" -ForegroundColor Red
    Write-Host "Please run: python -m venv s2t" -ForegroundColor Yellow
    exit 1
}

# Activate environment
Write-Host "🔄 Activating Python environment..." -ForegroundColor Blue
& ".\s2t\Scripts\activate.bat"

# Check if we want Docker or Python
param(
    [string]$mode = "interactive"
)

if ($mode -eq "docker") {
    Write-Host "🐳 Starting Docker deployment..." -ForegroundColor Green
    & ".\deployment\start.bat"
}
elseif ($mode -eq "python") {
    Write-Host "🐍 Starting Python CLI..." -ForegroundColor Green  
    python src\main.py
}
else {
    Write-Host "🎙️ Vietnamese Speech-to-Text System" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Choose your deployment method:" -ForegroundColor Yellow
    Write-Host "1. 🐳 Docker (Recommended for production)" -ForegroundColor White
    Write-Host "2. 🐍 Python CLI (Direct execution)" -ForegroundColor White
    Write-Host "3. 🛠️ Development mode" -ForegroundColor White
    Write-Host ""
    
    $choice = Read-Host "Enter your choice (1-3)"
    
    switch ($choice) {
        "1" { 
            Write-Host "🐳 Starting Docker..." -ForegroundColor Green
            & ".\deployment\start.bat"
        }
        "2" { 
            Write-Host "🐍 Starting Python CLI..." -ForegroundColor Green
            python src\main.py 
        }
        "3" { 
            Write-Host "🛠️ Starting Development Docker..." -ForegroundColor Green
            & ".\deployment\start-dev.bat"
        }
        default { 
            Write-Host "❌ Invalid choice" -ForegroundColor Red 
        }
    }
}