@echo off
REM LoRA Training Tool - Setup Script
REM Creates virtual environment and installs dependencies

echo ========================================
echo LoRA Training Tool - Environment Setup
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.8 or higher.
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [1/4] Checking Python version...
python --version
echo.

REM Check if virtual environment already exists
if exist "lora\Scripts\activate.bat" (
    echo [INFO] Virtual environment already exists.
    choice /C YN /M "Do you want to recreate it? (This will delete existing environment)"
    if errorlevel 2 (
        echo [INFO] Using existing environment.
        goto :install_deps
    )
    echo [INFO] Removing existing environment...
    rmdir /s /q lora
)

REM Create virtual environment
echo [2/4] Creating virtual environment...
python -m venv lora
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment!
    pause
    exit /b 1
)
echo [OK] Virtual environment created: lora\
echo.

:install_deps
REM Activate virtual environment
echo [3/4] Activating virtual environment...
call lora\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment!
    pause
    exit /b 1
)
echo [OK] Virtual environment activated
echo.

REM Upgrade pip
echo [4/4] Installing dependencies...
echo.
echo [4.1] Upgrading pip...
python -m pip install --upgrade pip
echo.

REM Install requirements
echo [4.2] Installing packages from requirements.txt...
echo This may take 5-15 minutes depending on your internet speed...
echo.
pip install -r requirements.txt
if errorlevel 1 (
    echo.
    echo [WARNING] Some packages failed to install!
    echo You may need to install CUDA manually for GPU support.
    echo.
    echo For NVIDIA GPUs, visit: https://pytorch.org/get-started/locally/
    echo.
    pause
    exit /b 1
)

echo.
echo ========================================
echo Setup Complete!
echo ========================================
echo.
echo Virtual environment: lora\
echo Python executable: lora\Scripts\python.exe
echo.
echo To activate the environment manually:
echo   lora\Scripts\activate
echo.
echo Next steps:
echo   1. Prepare your dataset in data\train\
echo   2. Run: scripts\setup\preprocess.bat (to validate dataset)
echo   3. Run: scripts\setup\train.bat (to start training)
echo.
echo Or use the guided wizard:
echo   scripts\setup\quickstart.bat
echo.
pause
