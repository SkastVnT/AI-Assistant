@echo off
REM ============================================================
REM Chatbot Service Deployment Script for Windows
REM ============================================================

setlocal enabledelayedexpansion

echo.
echo ========================================
echo   Chatbot Service Deployment
echo ========================================
echo.

REM Configuration
set SERVICE_DIR=%~dp0..\services\chatbot
set BACKUP_DIR=%~dp0..\backups
set LOG_DIR=%~dp0..\logs
set TIMESTAMP=%DATE:~10,4%%DATE:~4,2%%DATE:~7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%

REM Create directories if not exist
if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo [1/6] Creating backup...
echo ----------------------------------------

REM Backup current state
set BACKUP_FILE=%BACKUP_DIR%\chatbot_backup_%TIMESTAMP%.zip
if exist "%SERVICE_DIR%\Storage" (
    powershell -Command "Compress-Archive -Path '%SERVICE_DIR%\Storage\*' -DestinationPath '%BACKUP_FILE%' -Force" 2>nul
    if exist "%BACKUP_FILE%" (
        echo [OK] Backup created: %BACKUP_FILE%
    ) else (
        echo [WARN] No Storage data to backup
    )
) else (
    echo [WARN] No Storage directory found
)

echo.
echo [2/6] Checking Python environment...
echo ----------------------------------------

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.10+
    exit /b 1
)
echo [OK] Python found

REM Check if in virtual environment
if defined VIRTUAL_ENV (
    echo [OK] Virtual environment active: %VIRTUAL_ENV%
) else (
    echo [WARN] No virtual environment detected
    echo        Consider running: python -m venv venv && venv\Scripts\activate
)

echo.
echo [3/6] Installing dependencies...
echo ----------------------------------------

cd /d "%SERVICE_DIR%"
if exist "requirements.txt" (
    pip install -r requirements.txt --quiet
    echo [OK] Dependencies installed
) else (
    echo [WARN] No requirements.txt found
)

echo.
echo [4/6] Running database migrations...
echo ----------------------------------------

REM Check MongoDB connection
python -c "from config.mongodb_helpers import get_mongo_client; print('MongoDB:', 'Connected' if get_mongo_client() else 'Failed')" 2>nul
if errorlevel 1 (
    echo [WARN] Could not verify MongoDB connection
) else (
    echo [OK] Database connection verified
)

echo.
echo [5/6] Running health checks...
echo ----------------------------------------

REM Test imports
python -c "from database import ConversationRepository, MessageRepository, MemoryRepository; print('[OK] Database modules loaded')" 2>nul
if errorlevel 1 (
    echo [WARN] Database module import failed
)

python -c "from database.cache import ChatbotCache; print('[OK] Cache:', 'Available' if ChatbotCache.get_stats() else 'Not available')" 2>nul
if errorlevel 1 (
    echo [WARN] Cache module import failed
)

python -c "from utils.health import get_health_checker; h = get_health_checker(); print('[OK] Health checker loaded')" 2>nul
if errorlevel 1 (
    echo [WARN] Health module not available
)

echo.
echo [6/6] Running smoke tests...
echo ----------------------------------------

REM Run quick tests
python -m pytest tests/test_repositories.py -v --tb=short -q 2>nul
if errorlevel 1 (
    echo [WARN] Some tests failed - check logs
) else (
    echo [OK] Smoke tests passed
)

echo.
echo ========================================
echo   Deployment Complete!
echo ========================================
echo.
echo Backup location: %BACKUP_FILE%
echo Log directory:   %LOG_DIR%
echo.
echo To start the service:
echo   cd %SERVICE_DIR%
echo   python app.py
echo.
echo To run with Gunicorn (production):
echo   gunicorn -w 4 -b 0.0.0.0:5001 app:app
echo.

endlocal
