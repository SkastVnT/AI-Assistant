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

cd services\image-upscale

REM Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    echo Using virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Using global Python...
)

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
