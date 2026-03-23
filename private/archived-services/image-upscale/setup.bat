@echo off
REM Setup script for upscale tool on Windows
echo ========================================
echo Upscale Tool - Setup Script
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.8 or higher.
    pause
    exit /b 1
)

echo [1/4] Checking Python version...
python --version

echo.
echo [2/4] Installing dependencies...
pip install --upgrade pip
pip install -e .

if errorlevel 1 (
    echo [ERROR] Failed to install dependencies!
    pause
    exit /b 1
)

echo.
echo [3/4] Creating necessary directories...
if not exist "models" mkdir models
if not exist "outputs" mkdir outputs

echo.
echo [4/4] Checking if you want to download models now...
set /p DOWNLOAD="Download pretrained models now? (y/n): "
if /i "%DOWNLOAD%"=="y" (
    echo.
    echo Downloading models...
    python models\download_models.py
)

echo.
echo ========================================
echo Setup complete!
echo ========================================
echo.
echo Quick start:
echo   1. Download models: python models\download_models.py
echo   2. Run CLI: upscale-tool upscale -i input.jpg -o output.png
echo   3. Run Web UI: python -m upscale_tool.web_ui
echo.
echo See QUICKSTART.md for more examples.
echo.
pause
