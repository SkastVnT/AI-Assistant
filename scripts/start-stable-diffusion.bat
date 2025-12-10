@echo off
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
