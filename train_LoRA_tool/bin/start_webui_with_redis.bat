@echo off
REM Start LoRA Training WebUI with Redis
REM Enhanced version with dependency checks and Redis support

echo ===============================================
echo LoRA Training WebUI v2.3.1
echo ===============================================
echo.

REM Check if virtual environment exists
if not exist ".\lora\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo Please run setup.bat first to create the environment.
    pause
    exit /b 1
)

REM Activate virtual environment
echo [1/4] Activating virtual environment...
call .\lora\Scripts\activate.bat

REM Check Redis connection (optional)
echo.
echo [2/4] Checking Redis connection...
docker ps --filter "name=redis" --format "{{.Names}}" | findstr redis >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] Redis container is running
    set REDIS_HOST=localhost
    set REDIS_PORT=6379
) else (
    echo [WARNING] Redis not running - starting Redis container...
    docker run -d -p 6379:6379 --name ai-assistant-redis redis:7-alpine >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] Redis started successfully
        timeout /t 2 >nul
        set REDIS_HOST=localhost
        set REDIS_PORT=6379
    ) else (
        echo [WARNING] Could not start Redis - will run in fallback mode
        echo WebUI will work but without caching features
    )
)

REM Install/update dependencies
echo.
echo [3/4] Checking dependencies...
pip install --quiet --upgrade ^
    flask ^
    flask-socketio ^
    flask-cors ^
    python-socketio ^
    eventlet ^
    redis ^
    pillow

echo [OK] All dependencies installed

REM Set environment variables
set FLASK_PORT=7860
set FLASK_DEBUG=False
set PYTHONUNBUFFERED=1

REM Check if .env file exists
if not exist ".env" (
    echo.
    echo [WARNING] .env file not found!
    echo Creating default .env file...
    (
        echo # Redis Configuration
        echo REDIS_HOST=localhost
        echo REDIS_PORT=6379
        echo.
        echo # Gemini API Key ^(get from https://aistudio.google.com/app/apikey^)
        echo GEMINI_API_KEY=your-api-key-here
        echo.
        echo # Training Configuration
        echo OUTPUT_DIR=./output
        echo MODELS_DIR=./models
    ) > .env
    echo [OK] Created .env file - please edit it with your API keys
)

REM Start WebUI
echo.
echo [4/4] Starting WebUI server...
echo.
echo ===============================================
echo   LoRA Training WebUI
echo ===============================================
echo   URL:      http://127.0.0.1:7860
echo   Redis:    %REDIS_HOST%:%REDIS_PORT%
echo   Logs:     ./logs/
echo ===============================================
echo.
echo Press Ctrl+C to stop the server
echo.

REM Run WebUI
python webui.py --host 127.0.0.1 --port 7860

REM Cleanup on exit
echo.
echo WebUI stopped.
pause
