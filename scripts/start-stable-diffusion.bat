@echo off
REM Force UTF-8 encoding to prevent Unicode errors
chcp 65001 >nul 2>&1

REM Navigate to project root (parent of scripts folder)
cd /d "%~dp0.."

echo ========================================
echo   Starting Stable Diffusion WebUI
echo ========================================
echo.
echo Service: AI Image Generation
echo Port: 7861
echo Path: services/stable-diffusion/
echo.
echo Features:
echo   - Text-to-Image
echo   - Image-to-Image
echo   - Inpainting
echo   - LoRA/VAE Support
echo   - ControlNet
echo.

REM Setup virtual environment and dependencies for other services
REM Note: Stable Diffusion has its own venv managed by webui.bat
call "%~dp0setup-venv.bat"
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to setup main environment
    pause
    exit /b 1
)

cd services\stable-diffusion

echo.
echo Starting Stable Diffusion WebUI...
echo.
echo NOTE: This may take a while on first run...
echo Access at: http://localhost:7861
echo.

REM Check if webui.bat exists
if exist "webui.bat" (
    call webui.bat --port 7861 --api
) else (
    echo ERROR: webui.bat not found!
    echo Please ensure Stable Diffusion is properly installed.
    pause
    exit /b 1
)

pause
