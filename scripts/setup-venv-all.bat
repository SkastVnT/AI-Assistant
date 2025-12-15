@echo off
setlocal enabledelayedexpansion
title AI Assistant - Setup Virtual Environment
color 0A

REM Get the project root (parent of scripts directory)
cd /d "%~dp0.."

echo ================================================================================
echo.
echo              Setup Virtual Environment for All Services
echo.
echo ================================================================================
echo.

REM Check if .venv exists
if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Virtual environment already exists
    echo        Checking installed packages...
    echo.
    
    REM Activate existing venv
    call .venv\Scripts\activate.bat
    if errorlevel 1 (
        echo [ERROR] Failed to activate virtual environment
        pause
        exit /b 1
    )
    
    REM Check if key packages are installed
    echo Checking for required packages: flask, torch, transformers, gradio...
    set NEED_INSTALL=0
    
    pip show flask >nul 2>&1
    if errorlevel 1 set NEED_INSTALL=1
    
    pip show torch >nul 2>&1
    if errorlevel 1 set NEED_INSTALL=1
    
    pip show transformers >nul 2>&1
    if errorlevel 1 set NEED_INSTALL=1
    
    pip show gradio >nul 2>&1
    if errorlevel 1 set NEED_INSTALL=1
    
    if !NEED_INSTALL!==1 (
        echo.
        echo [WARNING] Some required packages are missing
        echo.
        echo [Step 1/2] Upgrading pip...
        python.exe -m pip install --upgrade pip
        echo.
        echo [Step 2/2] Installing missing packages from requirements.txt...
        echo This may take 10-15 minutes. Please wait...
        echo.
        pip install -r requirements.txt
        if errorlevel 1 (
            echo.
            echo [ERROR] Failed to install packages
            pause
            exit /b 1
        )
        echo.
        echo ================================================================================
        echo                    ✅ Setup Complete!
        echo ================================================================================
        echo.
        echo All packages installed successfully!
    ) else (
        echo.
        echo ================================================================================
        echo                    ✅ Environment Ready!
        echo ================================================================================
        echo.
        echo [OK] All required packages are already installed
        echo.
        echo No installation needed. Your environment is ready to use!
    )
    
) else (
    echo [INFO] Virtual environment not found
    echo        Creating new virtual environment...
    echo.
    
    REM Create new venv
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        echo.
        echo Troubleshooting:
        echo   - Make sure Python is installed and in PATH
        echo   - Try: python --version
        echo   - Required: Python 3.10.x or 3.11.x
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
    echo.
    
    REM Activate new venv
    call .venv\Scripts\activate.bat
    if errorlevel 1 (
        echo [ERROR] Failed to activate virtual environment
        pause
        exit /b 1
    )
    echo [OK] Virtual environment activated
    echo.
    
    REM Upgrade pip
    echo [Step 1/2] Upgrading pip...
    python.exe -m pip install --upgrade pip
    echo.
    
    REM Install requirements
    echo [Step 2/2] Installing all packages from requirements.txt...
    echo This may take 10-15 minutes. Please wait...
    echo.
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to install packages
        pause
        exit /b 1
    )
    echo.
    echo ================================================================================
    echo                    ✅ Setup Complete!
    echo ================================================================================
    echo.
    echo Virtual environment created and all packages installed successfully!
)

echo.
echo Next steps:
echo   1. Start individual services from menu
echo   2. Or start all services with option 'A'
echo   3. Run tests with option 'T'
echo.
echo ================================================================================
echo.
pause
