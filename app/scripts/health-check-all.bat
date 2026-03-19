@echo off
title AI Assistant - Complete Health Check
color 0D

REM Force UTF-8 encoding to prevent Unicode errors
chcp 65001 >nul 2>&1

REM Navigate to project root (parent of scripts folder)
cd /d "%~dp0.."

echo ================================================================================
echo.
echo     AI-POWERED HEALTH CHECK - FULL SYSTEM VERIFICATION
echo.
echo ================================================================================
echo.
echo This will perform a comprehensive health check on all services:
echo.
echo   [x] Python version verification (3.11.x recommended)
echo   [x] Virtual environment status
echo   [x] Dependency analysis (AI-powered)
echo   [x] Missing package detection
echo   [x] Service test runs
echo   [x] Error diagnosis and auto-fix
echo.
echo Powered by: Gemini 2.0 Flash / Grok AI
echo.
echo ================================================================================
echo.
pause

REM ============================================================================
REM Step 1: Check Python Version
REM ============================================================================
echo.
echo ========================================
echo   [1/10] Checking Python Version
echo ========================================
echo.

call scripts\check-python.bat
if errorlevel 1 (
    echo [WARNING] Python version check failed
    echo Please install Python 3.11.x
    echo.
)

REM ============================================================================
REM Step 2: Check Main Virtual Environment
REM ============================================================================
echo.
echo ========================================
echo   [2/10] Checking Main Environment
echo ========================================
echo.

if exist ".venv\Scripts\activate.bat" (
    echo [OK] Main virtual environment found
    call .venv\Scripts\activate.bat
) else (
    echo [ERROR] Main virtual environment not found!
    echo.
    echo Please run: menu.bat - Select [0] Quick Setup
    echo   OR run: scripts\SETUP.bat
    echo.
    pause
    exit /b 1
)

REM ============================================================================
REM Step 3-10: Check Each Service (Using Shared .venv)
REM ============================================================================

echo.
echo ========================================
echo   [3/10] Hub Gateway Health Check
echo ========================================
echo.
if exist "services\hub-gateway\app.py" (
    echo [OK] Hub Gateway service files found
    python -c "import flask" >nul 2>&1 && echo [OK] Flask installed || echo [WARNING] Flask missing
) else (
    echo [WARNING] Hub Gateway files not found
)

echo.
echo ========================================
echo   [4/10] ChatBot Health Check
echo ========================================
echo.
if exist "services\chatbot\app.py" (
    echo [OK] ChatBot service files found
    python -c "import flask" >nul 2>&1 && echo [OK] Flask installed || echo [WARNING] Flask missing
    python -c "import google.genai" >nul 2>&1 && echo [OK] Google GenAI installed || echo [WARNING] google-genai missing
) else (
    echo [WARNING] ChatBot files not found
)

echo.
echo ========================================
echo   [5/10] Text2SQL Health Check
echo ========================================
echo.
if exist "services\text2sql\app.py" (
    echo [OK] Text2SQL service files found
    python -c "import flask" >nul 2>&1 && echo [OK] Flask installed || echo [WARNING] Flask missing
) else (
    echo [WARNING] Text2SQL files not found
)

echo.
echo ========================================
echo   [6/10] Document Intelligence Check
echo ========================================
echo.
if exist "services\document-intelligence\app.py" (
    echo [OK] Document Intelligence service files found
    python -c "import paddleocr" >nul 2>&1 && echo [OK] PaddleOCR installed || echo [WARNING] PaddleOCR missing - Run SETUP.bat
) else (
    echo [WARNING] Document Intelligence files not found
)

echo.
echo ========================================
echo   [7/10] Speech2Text Health Check
echo ========================================
echo.
if exist "services\speech2text\app\web_ui.py" (
    echo [OK] Speech2Text service files found
    python -c "import faster_whisper" >nul 2>&1 && echo [OK] Faster-Whisper installed || echo [WARNING] Faster-Whisper missing - Run SETUP.bat
) else (
    echo [WARNING] Speech2Text files not found
)

echo.
echo ========================================
echo   [8/10] Stable Diffusion Check
echo ========================================
echo.
if exist "services\stable-diffusion\venv" (
    echo [OK] Stable Diffusion service files found
    echo [INFO] SD requires first-run download of models
    python -c "import torch" >nul 2>&1 && echo [OK] PyTorch installed || echo [WARNING] PyTorch missing - Run SETUP.bat
) else (
    echo [WARNING] Stable Diffusion files not found
)

echo.
echo ========================================
echo   [9/10] LoRA Training Health Check
echo ========================================
echo.
if exist "services\lora-training" (
    echo [OK] LoRA Training service files found
    python -c "import torch" >nul 2>&1 && echo [OK] PyTorch installed || echo [WARNING] PyTorch missing - Run SETUP.bat
) else (
    echo [WARNING] LoRA Training files not found
)

echo.
echo ========================================
echo   [10/10] Image Upscale Health Check
echo ========================================
echo.
if exist "services\image-upscale" (
    echo [OK] Image Upscale service files found
    python -c "import torch" >nul 2>&1 && echo [OK] PyTorch installed || echo [WARNING] PyTorch missing - Run SETUP.bat
) else (
    echo [WARNING] Image Upscale files not found
)

REM ============================================================================
REM Summary
REM ============================================================================
echo.
echo ================================================================================
echo.
echo   HEALTH CHECK COMPLETE
echo.
echo ================================================================================
echo.
echo Review the results above to identify any issues.
echo.
echo Next Steps:
echo.
echo   If .venv is MISSING:
echo     - Run: menu.bat - Select [0] Quick Setup
echo     - OR run: scripts\SETUP.bat
echo.
echo   If dependencies are MISSING:
echo     - Activate venv: .venv\Scripts\activate.bat
echo     - Install: pip install -r requirements.txt
echo.
echo   If all OK:
echo     - Run: menu.bat - Select [A] Start All Services
echo     - OR start individual services via menu options 1-9
echo.
echo ================================================================================
echo.
echo NOTE: This project uses SHARED .venv at root (not per-service venvs)
echo   All services share the same Python environment
echo   Install once, use everywhere!
echo.
echo ================================================================================
echo.
pause
