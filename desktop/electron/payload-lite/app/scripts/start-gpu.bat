@echo off
REM =============================================================================
REM AI-Assistant - Start with GPU Services
REM =============================================================================
REM Starts all services including GPU-accelerated ones
REM Requires NVIDIA GPU with Docker GPU support
REM =============================================================================

echo.
echo  ========================================
echo   AI-Assistant GPU Start
echo  ========================================
echo.

REM Check for NVIDIA GPU
nvidia-smi >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [WARN] NVIDIA GPU not detected or nvidia-smi not available
    echo GPU services may not work correctly
    echo.
)

REM Start all services including GPU profile
echo Starting all services (including GPU)...
docker-compose --profile gpu up -d

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Failed to start services
    echo.
    echo If GPU services failed, try starting without GPU:
    echo   docker-compose up -d
    pause
    exit /b 1
)

echo.
echo ========================================
echo  All Services Started!
echo ========================================
echo.
echo  Core Services:
echo    MongoDB:              http://localhost:27017
echo    Redis:                localhost:6379
echo    Hub Gateway:          http://localhost:3000
echo    Chatbot:              http://localhost:5000
echo.
echo  GPU Services:
echo    Stable Diffusion:     http://localhost:7860
echo    Speech2Text:          http://localhost:5001
echo    Image Upscale:        http://localhost:7863
echo    LoRA Training:        http://localhost:7862
echo.
echo ========================================

pause
