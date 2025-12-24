@echo off
REM ============================================================================
REM Build Script - ChatBot Service
REM AI-Assistant Project
REM ============================================================================
REM Description: Automated build script with dependency validation and testing
REM Author: SkastVnT
REM Version: 1.0.0
REM ============================================================================

REM Force UTF-8 encoding to prevent Unicode errors
chcp 65001 >nul 2>&1

setlocal enabledelayedexpansion

REM Colors for output (Windows 10+)
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "RESET=[0m"

REM Script configuration
set "SERVICE_NAME=ChatBot"
set "VENV_NAME=venv_chatbot"
set "PYTHON_VERSION=3.10"
set "REQUIREMENTS_FILE=requirements.txt"
set "TEST_DIR=tests"

echo.
echo %BLUE%============================================================%RESET%
echo %BLUE%  BUILD SCRIPT - %SERVICE_NAME% SERVICE%RESET%
echo %BLUE%============================================================%RESET%
echo.

REM ============================================================================
REM STEP 1: Check Python Installation
REM ============================================================================
echo %YELLOW%[STEP 1/7]%RESET% Checking Python installation...

python --version >nul 2>&1
if errorlevel 1 (
    echo %RED%[ERROR]%RESET% Python is not installed or not in PATH!
    echo.
    echo Please install Python %PYTHON_VERSION% or higher from:
    echo https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VER=%%i
echo %GREEN%[OK]%RESET% Python %PYTHON_VER% found

REM Check Python version (at least 3.10)
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VER%") do (
    set MAJOR=%%a
    set MINOR=%%b
)

if %MAJOR% LSS 3 (
    echo %RED%[ERROR]%RESET% Python 3.10+ required, found %PYTHON_VER%
    pause
    exit /b 1
)

if %MAJOR% EQU 3 if %MINOR% LSS 10 (
    echo %RED%[ERROR]%RESET% Python 3.10+ required, found %PYTHON_VER%
    pause
    exit /b 1
)

echo.

REM ============================================================================
REM STEP 2: Check/Create Virtual Environment
REM ============================================================================
echo %YELLOW%[STEP 2/7]%RESET% Checking virtual environment...

if exist "%VENV_NAME%\" (
    echo %GREEN%[OK]%RESET% Virtual environment found: %VENV_NAME%
) else (
    echo %YELLOW%[INFO]%RESET% Creating virtual environment: %VENV_NAME%
    python -m venv %VENV_NAME%
    if errorlevel 1 (
        echo %RED%[ERROR]%RESET% Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo %GREEN%[OK]%RESET% Virtual environment created
)

echo.

REM ============================================================================
REM STEP 3: Activate Virtual Environment
REM ============================================================================
echo %YELLOW%[STEP 3/7]%RESET% Activating virtual environment...

call %VENV_NAME%\Scripts\activate.bat
if errorlevel 1 (
    echo %RED%[ERROR]%RESET% Failed to activate virtual environment!
    pause
    exit /b 1
)

echo %GREEN%[OK]%RESET% Virtual environment activated
echo.

REM ============================================================================
REM STEP 4: Upgrade pip
REM ============================================================================
echo %YELLOW%[STEP 4/7]%RESET% Upgrading pip...

python -m pip install --upgrade pip >nul 2>&1
if errorlevel 1 (
    echo %RED%[ERROR]%RESET% Failed to upgrade pip!
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('pip --version 2^>^&1') do set PIP_VER=%%i
echo %GREEN%[OK]%RESET% pip %PIP_VER%
echo.

REM ============================================================================
REM STEP 5: Install/Check Dependencies
REM ============================================================================
echo %YELLOW%[STEP 5/7]%RESET% Checking dependencies from %REQUIREMENTS_FILE%...

if not exist "%REQUIREMENTS_FILE%" (
    echo %RED%[ERROR]%RESET% %REQUIREMENTS_FILE% not found!
    pause
    exit /b 1
)

REM Get installed packages
pip list --format=freeze > temp_installed.txt

REM Parse requirements and check each package
set MISSING_COUNT=0
set TOTAL_COUNT=0

echo.
echo Checking required packages:
echo ----------------------------------------

for /f "usebackq tokens=1 delims==><!#" %%p in ("%REQUIREMENTS_FILE%") do (
    set "PACKAGE=%%p"
    set "PACKAGE=!PACKAGE: =!"
    
    REM Skip empty lines and comments
    if not "!PACKAGE!"=="" if not "!PACKAGE:~0,1!"=="#" (
        set /a TOTAL_COUNT+=1
        
        REM Check if package is installed
        findstr /i /b "!PACKAGE!" temp_installed.txt >nul 2>&1
        if errorlevel 1 (
            echo %RED%[MISSING]%RESET% !PACKAGE!
            set /a MISSING_COUNT+=1
        ) else (
            echo %GREEN%[OK]%RESET% !PACKAGE!
        )
    )
)

del temp_installed.txt

echo ----------------------------------------
echo Total: %TOTAL_COUNT% packages, Missing: %MISSING_COUNT%
echo.

if %MISSING_COUNT% GTR 0 (
    echo %YELLOW%[INFO]%RESET% Installing missing packages...
    echo.
    
    pip install -r %REQUIREMENTS_FILE%
    if errorlevel 1 (
        echo.
        echo %RED%[ERROR]%RESET% Failed to install some dependencies!
        echo.
        echo Common issues:
        echo - PyTorch: Install from https://pytorch.org/get-started/locally/
        echo - bitsandbytes: Windows requires Visual C++ Build Tools
        echo.
        echo See BUILD_GUIDE.md for detailed troubleshooting
        pause
        exit /b 1
    )
    
    echo.
    echo %GREEN%[OK]%RESET% All dependencies installed successfully
) else (
    echo %GREEN%[OK]%RESET% All dependencies already installed
)

echo.

REM ============================================================================
REM STEP 6: Verify Critical Packages
REM ============================================================================
echo %YELLOW%[STEP 6/7]%RESET% Verifying critical packages...

set CRITICAL_FAILED=0

REM Check Flask
python -c "import flask; print('Flask:', flask.__version__)" >nul 2>&1
if errorlevel 1 (
    echo %RED%[FAIL]%RESET% Flask
    set CRITICAL_FAILED=1
) else (
    for /f "tokens=2" %%v in ('python -c "import flask; print('Flask:', flask.__version__)" 2^>^&1') do echo %GREEN%[OK]%RESET% Flask %%v
)

REM Check google-genai (new package name)
python -c "import google.genai" >nul 2>&1
if errorlevel 1 (
    echo %RED%[FAIL]%RESET% google-genai
    set CRITICAL_FAILED=1
) else (
    echo %GREEN%[OK]%RESET% google-genai
)

REM Check Pillow
python -c "import PIL; print(PIL.__version__)" >nul 2>&1
if errorlevel 1 (
    echo %RED%[FAIL]%RESET% Pillow
    set CRITICAL_FAILED=1
) else (
    for /f "tokens=1" %%v in ('python -c "import PIL; print(PIL.__version__)" 2^>^&1') do echo %GREEN%[OK]%RESET% Pillow %%v
)

REM Check PyTorch (optional but recommended)
python -c "import torch; print(torch.__version__)" >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%[WARN]%RESET% PyTorch (optional - for local models)
) else (
    for /f "tokens=1" %%v in ('python -c "import torch; print(torch.__version__)" 2^>^&1') do echo %GREEN%[OK]%RESET% PyTorch %%v
    
    REM Check CUDA if PyTorch is installed
    python -c "import torch; print('CUDA:', torch.cuda.is_available())" >nul 2>&1
    for /f "tokens=2" %%c in ('python -c "import torch; print(torch.cuda.is_available())" 2^>^&1') do (
        if "%%c"=="True" (
            echo %GREEN%[OK]%RESET% CUDA available
        ) else (
            echo %YELLOW%[INFO]%RESET% CUDA not available (CPU mode)
        )
    )
)

if %CRITICAL_FAILED% GTR 0 (
    echo.
    echo %RED%[ERROR]%RESET% Some critical packages failed to import!
    echo Please check the error messages above.
    pause
    exit /b 1
)

echo.

REM ============================================================================
REM STEP 7: Run Tests (if pytest available)
REM ============================================================================
echo %YELLOW%[STEP 7/7]%RESET% Running tests...

python -c "import pytest" >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%[SKIP]%RESET% pytest not installed, skipping tests
) else (
    if exist "%TEST_DIR%" (
        echo Running pytest in %TEST_DIR%...
        echo.
        
        pytest %TEST_DIR% -v --tb=short
        if errorlevel 1 (
            echo.
            echo %YELLOW%[WARN]%RESET% Some tests failed, but build continues
        ) else (
            echo.
            echo %GREEN%[OK]%RESET% All tests passed
        )
    ) else (
        echo %YELLOW%[INFO]%RESET% No tests directory found
    )
)

echo.

REM ============================================================================
REM BUILD COMPLETE
REM ============================================================================
echo %GREEN%============================================================%RESET%
echo %GREEN%  BUILD COMPLETE - %SERVICE_NAME% SERVICE%RESET%
echo %GREEN%============================================================%RESET%
echo.
echo Next steps:
echo 1. Configure .env file with your API keys (optional)
echo 2. Start the service from menu or run: scripts\start-chatbot.bat
echo 3. Access at: http://localhost:5000
echo.
echo Note: Service will start without API keys but some features may be limited.
echo.

pause
