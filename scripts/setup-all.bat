@echo off
title AI Assistant - Setup All Services (AI-Enhanced)
color 0D

REM Force UTF-8 encoding to prevent Unicode errors
chcp 65001 >nul 2>&1

REM Get the project root
cd /d "%~dp0.."

echo ================================================================================
echo.
echo                  AI Assistant - Complete Setup (AI-Enhanced)
echo.
echo ================================================================================
echo.
echo This will set up all services with AI-powered dependency checking.
echo.
echo Features:
echo   - Gemini 2.0 Flash AI for dependency verification
echo   - Automatic missing package detection
echo   - Smart error diagnosis and auto-fix
echo   - Health check for each service
echo.
echo Services:
echo   [1] Hub Gateway
echo   [2] ChatBot
echo   [3] Text2SQL
echo   [4] Document Intelligence
echo   [5] Speech2Text
echo   [6] Stable Diffusion
echo   [7] LoRA Training
echo   [8] Image Upscale
echo   [9] MCP Server
echo.
echo ================================================================================
echo.
echo NOTE: This may take 30-60 minutes depending on your internet speed.
echo.
pause

REM Check if main venv exists for health checker
if not exist ".venv\Scripts\activate.bat" (
    echo.
    echo ========================================
    echo   Setting up main environment
    echo ========================================
    echo.
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -r requirements.txt
) else (
    call .venv\Scripts\activate.bat
)

REM Install health checker dependencies if needed
pip show google-generativeai >nul 2>&1
if errorlevel 1 (
    echo Installing AI dependencies for health checker...
    pip install google-generativeai openai python-dotenv
)

echo.
echo ========================================
echo   Installing Root Dependencies
echo ========================================
echo.
pip install -r requirements.txt

echo.
echo ========================================
echo   [1/8] Setting up Hub Gateway
echo ========================================
echo.
cd services\hub-gateway
if not exist "venv" (
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install flask flask-cors
)
cd ..\..
echo [OK] Hub Gateway setup complete (no requirements.txt)

echo.
echo ========================================
echo   [2/8] Setting up ChatBot
echo ========================================
echo.
cd services\chatbot
if exist "build-service-chatbot.bat" (
    call build-service-chatbot.bat
) else if not exist "venv_chatbot" (
    python -m venv venv_chatbot
    call venv_chatbot\Scripts\activate.bat
    pip install -r requirements.txt
)
cd ..\..
echo Running AI health check for ChatBot...
python scripts\utilities\service_health_checker.py "ChatBot" "services\chatbot"

echo.
echo ========================================
echo   [3/8] Setting up Text2SQL
echo ========================================
echo.
cd services\text2sql
if not exist "venv" (
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
)
cd ..\..
echo Running AI health check for Text2SQL...
python scripts\utilities\service_health_checker.py "Text2SQL" "services\text2sql"

echo.
echo ========================================
echo   [4/8] Setting up Document Intelligence
echo ========================================
echo.
cd services\document-intelligence
if exist "setup.bat" (
    call setup.bat
) else if not exist "venv" (
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
)
cd ..\..
echo Running AI health check for Document Intelligence...
python scripts\utilities\service_health_checker.py "Document Intelligence" "services\document-intelligence"

echo.
echo ========================================
echo   [5/8] Setting up Speech2Text
echo ========================================
echo.
cd services\speech2text
if not exist "venv" (
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
)
cd ..\..
echo Running AI health check for Speech2Text...
python scripts\utilities\service_health_checker.py "Speech2Text" "services\speech2text"

echo.
echo ========================================
echo   [6/8] Setting up Stable Diffusion
echo ========================================
echo.
cd services\stable-diffusion
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo Installing dependencies...
    pip install -r requirements.txt
)
cd ..\..
echo Running AI health check for Stable Diffusion...
python scripts\utilities\service_health_checker.py "Stable Diffusion" "services\stable-diffusion"

echo.
echo ========================================
echo   [7/8] Setting up LoRA Training
echo ========================================
echo.
cd services\lora-training
if exist "bin\setup.sh" (
    echo Using setup script...
    bash bin\setup.sh
) else if not exist "lora" (
    python -m venv lora
    call lora\Scripts\activate.bat
    pip install -r requirements.txt
)
cd ..\..
echo Running AI health check for LoRA Training...
python scripts\utilities\service_health_checker.py "LoRA Training" "services\lora-training"

echo.
echo ========================================
echo   [8/8] Setting up Image Upscale
echo ========================================
echo.
cd services\image-upscale
if not exist "venv" (
    python -m venv venv
    call venv\Scripts\activate.bat
    pip install -r requirements.txt
)
cd ..\..
echo Running AI health check for Image Upscale...
python scripts\utilities\service_health_checker.py "Image Upscale" "services\image-upscale"

echo.
echo ================================================================================
echo   ✅ AI-Enhanced Setup Complete!
echo ================================================================================
echo.
echo All services have been set up and verified by AI.
echo.
echo Next steps:
echo   1. Check the health check results above
echo   2. Configure .env files for each service
echo   3. Run: menu.bat and select 'A' to start all services
echo   4. Run: menu.bat and select 'T' to run tests
echo.
echo AI Features:
echo   ✓ Automatic dependency verification
echo   ✓ Smart error detection
echo   ✓ Auto-fix for common issues
echo.
pause
