@echo off
title AI Assistant - Setup All Services
color 0D

echo ================================================================================
echo.
echo                  AI Assistant - Complete Setup
echo.
echo ================================================================================
echo.
echo This will set up all services with their dependencies.
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
echo.
echo ================================================================================
echo.
echo NOTE: This may take 30-60 minutes depending on your internet speed.
echo.
pause

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
    pip install -r requirements.txt
)
cd ..\..

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

echo.
echo ========================================
echo   [6/8] Setting up Stable Diffusion
echo ========================================
echo.
cd services\stable-diffusion
echo Stable Diffusion will auto-setup on first run
echo Run: start-stable-diffusion.bat
cd ..\..

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

echo.
echo ================================================================================
echo   ✅ Setup Complete!
echo ================================================================================
echo.
echo Next steps:
echo   1. Configure .env files for each service
echo   2. Run: start-all.bat to start all services
echo   3. Run: test-all.bat to verify installation
echo.
pause
