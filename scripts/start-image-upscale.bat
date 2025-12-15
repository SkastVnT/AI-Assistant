@echo off
echo ========================================
echo   Starting Image Upscale Tool
echo ========================================
echo.
echo Service: AI Image Enhancement
echo Port: 7863
echo Path: services/image-upscale/
echo.
echo Features:
echo   - RealESRGAN (x2, x4)
echo   - SwinIR Real-SR
echo   - ScuNET GAN
echo   - Batch Processing
echo.

REM Setup virtual environment and dependencies
call "%~dp0setup-venv.bat"
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to setup environment
    pause
    exit /b 1
)

cd services\image-upscale

echo.
echo Starting Image Upscale Tool...
echo Access at: http://localhost:7863
echo.

REM Check if main script exists
if exist "src\upscale_tool\app.py" (
    python src\upscale_tool\app.py
) else if exist "app.py" (
    python app.py
) else (
    echo ERROR: Main script not found!
    echo Please check the installation.
    pause
    exit /b 1
)

pause
