@echo off
REM ============================================================================
REM Setup Virtual Environment & Dependencies (Simplified)
REM Activates .venv and installs missing dependencies
REM ============================================================================

title AI-Assistant - Virtual Environment Setup
color 0A
setlocal enabledelayedexpansion

REM Force UTF-8 encoding to prevent Unicode errors
chcp 65001 >nul 2>&1

REM Get project root (parent of scripts folder)
set "PROJECT_ROOT=%~dp0.."
cd /d "%PROJECT_ROOT%"

echo.
echo ============================================================================
echo   Virtual Environment Setup
echo ============================================================================
echo.

REM ============================================================================
REM Check if .venv exists
REM ============================================================================
if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found at .venv
    echo.
    echo Please run scripts\SETUP.bat first to create the environment.
    echo.
    pause
    exit /b 1
)

echo [OK] Virtual environment found
echo.

REM ============================================================================
REM Activate virtual environment
REM ============================================================================
echo [INFO] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment activated
echo.

REM ============================================================================
REM Check for missing critical packages
REM ============================================================================
echo [INFO] Checking installed packages...
echo.

set NEED_INSTALL=0

REM Check critical packages
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [MISSING] flask
    set NEED_INSTALL=1
)

python -c "import torch" >nul 2>&1
if errorlevel 1 (
    echo [MISSING] torch
    set NEED_INSTALL=1
)

python -c "from google import genai" >nul 2>&1
if errorlevel 1 (
    echo [MISSING] google-genai
    set NEED_INSTALL=1
)

python -c "import transformers" >nul 2>&1
if errorlevel 1 (
    echo [MISSING] transformers
    set NEED_INSTALL=1
)

python -c "import gradio" >nul 2>&1
if errorlevel 1 (
    echo [MISSING] gradio
    set NEED_INSTALL=1
)

REM ============================================================================
REM Install missing packages if needed
REM ============================================================================
if %NEED_INSTALL%==1 (
    echo.
    echo [WARNING] Some critical packages are missing
    echo.
    echo [INFO] Installing missing dependencies...
    echo [INFO] This may take several minutes...
    echo.
    
    REM Try requirements.txt first, but don't fail if it errors
    echo [Step 1/2] Attempting to install from requirements.txt...
    pip install -r requirements.txt 2>nul
    
    REM Install critical packages individually
    echo.
    echo [Step 2/2] Installing critical packages individually...
    echo.
    
    echo   [1/8] Flask web framework...
    python -m pip install flask flask-cors python-dotenv werkzeug --disable-pip-version-check
    
    echo   [2/8] Database drivers...
    python -m pip install pymongo dnspython redis --disable-pip-version-check
    
    echo   [3/8] NumPy...
    python -m pip install "numpy<2.0.0" --disable-pip-version-check
    
    echo   [4/8] PyTorch ^(this may take a while^)...
    python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 --disable-pip-version-check
    
    echo   [5/8] AI/ML transformers...
    python -m pip install transformers accelerate sentencepiece protobuf --disable-pip-version-check
    
    echo   [6/8] Semantic search...
    python -m pip install sentence-transformers scipy scikit-learn --disable-pip-version-check
    
    echo   [7/8] AI APIs...
    python -m pip install google-genai openai --disable-pip-version-check
    
    echo   [8/8] Gradio UI and utilities...
    python -m pip install gradio Pillow requests aiofiles pyyaml jsonschema tqdm --disable-pip-version-check
    
    echo.
    echo [OK] Critical packages installation completed
    echo [INFO] Some optional packages may need manual installation
) else (
    echo [OK] All critical packages are installed
)

echo.
echo ============================================================================
echo   ✅ Virtual Environment Ready
echo ============================================================================
echo.

exit /b 0

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
    echo Creating virtual environment at .venv with Python 3.11...
    python -m venv .venv
    
    if errorlevel 1 (
        echo.
        echo [ERROR] Failed to create virtual environment!
        echo Please check Python 3.11.x installation.
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
