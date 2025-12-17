@echo off
title AI Assistant - Start All Services
color 0A

REM Navigate to project root (parent of scripts folder)
cd /d "%~dp0.."

echo ================================================================================
echo.
echo     █████╗ ██╗    ██████╗ ██╗   ██╗██╗██╗     ██████╗ ███████╗██████╗ 
echo    ██╔══██╗██║    ██╔══██╗██║   ██║██║██║     ██╔══██╗██╔════╝██╔══██╗
echo    ███████║██║    ██████╔╝██║   ██║██║██║     ██║  ██║█████╗  ██████╔╝
echo    ██╔══██║██║    ██╔══██╗██║   ██║██║██║     ██║  ██║██╔══╝  ██╔══██╗
echo    ██║  ██║██║    ██████╔╝╚██████╔╝██║███████╗██████╔╝███████╗██║  ██║
echo    ╚═╝  ╚═╝╚═╝    ╚═════╝  ╚═════╝ ╚═╝╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═╝
echo.
echo                         Start All Services v2.3
echo ================================================================================
echo.
echo This will start all AI Assistant services in separate windows:
echo.
echo   [1] Hub Gateway            Port 3000  - API Orchestrator
echo   [2] ChatBot                Port 5000  - Multi-Model AI Chat
echo   [3] Text2SQL               Port 5002  - SQL Query Generation
echo   [4] Document Intelligence  Port 5003  - OCR + AI Analysis
echo   [5] Speech2Text            Port 5001  - Audio Transcription
echo   [6] Stable Diffusion       Port 7861  - Image Generation
echo   [7] LoRA Training          Port 7862  - Model Fine-tuning
echo   [8] Image Upscale          Port 7863  - Image Enhancement
echo.
echo ================================================================================
echo.
echo NOTE: Each service will open in a new window.
echo       You can close individual services by closing their windows.
echo.

REM Check Python version first
call "%~dp0check-python.bat"
echo.

REM Setup virtual environment and dependencies
echo Checking virtual environment and dependencies...
call "%~dp0setup-venv.bat"
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to setup environment
    pause
    exit /b 1
)

echo.
pause

echo.
echo [1/8] Starting Hub Gateway...
start "AI Hub Gateway - Port 3000" cmd /k "%~dp0start-hub-gateway.bat"
timeout /t 2 >nul

echo [2/8] Starting ChatBot Service...
start "ChatBot Service - Port 5000" cmd /k "%~dp0start-chatbot.bat"
timeout /t 2 >nul

echo [3/8] Starting Text2SQL Service...
start "Text2SQL Service - Port 5002" cmd /k "%~dp0start-text2sql.bat"
timeout /t 2 >nul

echo [4/8] Starting Document Intelligence...
start "Document Intelligence - Port 5003" cmd /k "%~dp0start-document-intelligence.bat"
timeout /t 2 >nul

echo [5/8] Starting Speech2Text Service...
start "Speech2Text Service - Port 7860" cmd /k "%~dp0start-speech2text.bat"
timeout /t 2 >nul

echo [6/8] Starting Stable Diffusion...
start "Stable Diffusion - Port 7861" cmd /k "%~dp0start-stable-diffusion.bat"
timeout /t 2 >nul

echo [7/8] Starting LoRA Training...
start "LoRA Training - Port 7862" cmd /k "%~dp0start-lora-training.bat"
timeout /t 2 >nul

echo [8/8] Starting Image Upscale...
start "Image Upscale - Port 7863" cmd /k "%~dp0start-image-upscale.bat"
timeout /t 2 >nul

echo.
echo ================================================================================
echo   ✅ All Services Started Successfully!
echo ================================================================================
echo.
echo Access the services at:
echo.
echo   🌐 Hub Gateway:            http://localhost:3000
echo   💬 ChatBot:                http://localhost:5001
echo   📊 Text2SQL:               http://localhost:5002
echo   📄 Document Intelligence:  http://localhost:5003
echo   🎤 Speech2Text:            http://localhost:7860
echo   🎨 Stable Diffusion:       http://localhost:7861
echo   🔧 LoRA Training:          http://localhost:7862
echo   📸 Image Upscale:          http://localhost:7863
echo.
echo ================================================================================
echo.
echo To stop all services, run: stop-all.bat
echo.
echo Press any key to exit this launcher window...
pause >nul
