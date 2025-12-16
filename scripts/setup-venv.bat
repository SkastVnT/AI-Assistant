@echo off
REM ============================================================================
REM Setup Virtual Environment & Dependencies
REM Activates .venv, checks pip list vs requirements.txt, installs if needed
REM ============================================================================

REM Get project root (parent of scripts folder)
set "PROJECT_ROOT=%~dp0.."
cd /d "%PROJECT_ROOT%"

echo.
echo ============================================================================
echo   Virtual Environment Setup
echo ============================================================================
echo.

REM Check if .venv exists
if exist ".venv\Scripts\activate.bat" (
    echo [FOUND] Virtual environment exists at .venv
    echo.
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
    
    echo.
    echo Checking installed packages...
    pip list > temp_pip_list.txt
    
    REM Check if key packages exist
    set NEED_INSTALL=0
    
    REM Check critical packages
    findstr /i "flask" temp_pip_list.txt >nul
    if errorlevel 1 set NEED_INSTALL=1
    findstr /i "torch" temp_pip_list.txt >nul
    if errorlevel 1 set NEED_INSTALL=1
    findstr /i "transformers" temp_pip_list.txt >nul
    if errorlevel 1 set NEED_INSTALL=1
    findstr /i "gradio" temp_pip_list.txt >nul
    if errorlevel 1 set NEED_INSTALL=1
    findstr /i "mcp" temp_pip_list.txt >nul
    if errorlevel 1 set NEED_INSTALL=1
    
    if "%NEED_INSTALL%"=="1" (
        echo [MISSING] Some critical packages not found
        echo.
        echo Upgrading pip...
        python.exe -m pip install --upgrade pip
        
        echo.
        echo Installing dependencies from requirements.txt...
        echo This may take 10-15 minutes for first install...
        echo.
        pip install -r requirements.txt
    ) else (
        echo [OK] Core dependencies found
        echo.
        echo Note: To ensure all packages are up-to-date, you can run:
        echo       pip install -r requirements.txt
    )
    
    del temp_pip_list.txt 2>nul
    
) else (
    echo [NOT FOUND] Virtual environment does not exist
    echo.
    echo Creating virtual environment at .venv...
    python -m venv .venv
    
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to create virtual environment!
        echo Please check Python installation.
        pause
        exit /b 1
    )
    
    echo [OK] Virtual environment created
    echo.
    echo Activating virtual environment...
    call .venv\Scripts\activate.bat
    
    echo.
    echo Upgrading pip...
    python.exe -m pip install --upgrade pip
    
    echo.
    echo Installing dependencies from requirements.txt...
    echo This may take 10-15 minutes for first install...
    echo.
    pip install -r requirements.txt
)

echo.
echo ============================================================================
echo [SUCCESS] Virtual environment ready
echo ============================================================================
echo.

exit /b 0
