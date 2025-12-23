@echo off
REM Force UTF-8 encoding to prevent Unicode errors
chcp 65001 >nul 2>&1

REM Navigate to project root (parent of scripts folder)
cd /d "%~dp0.."

echo ========================================
echo   Starting LoRA Training Tool
echo ========================================
echo.
echo Service: AI Model Fine-tuning
echo Port: 7862
echo Path: services/lora-training/
echo.
echo Features:
echo   - LoRA Model Training
echo   - Gemini AI Assistant
echo   - Dataset Tools (WD14 Tagger)
echo   - Redis Caching
echo   - Training Monitoring
echo.

REM Setup virtual environment and dependencies
call "%~dp0setup-venv.bat"
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to setup environment
    pause
    exit /b 1
)

cd services\lora-training

echo.
echo Starting LoRA Training WebUI...
echo Access at: http://localhost:7862
echo.
python webui.py --port 7862

pause
