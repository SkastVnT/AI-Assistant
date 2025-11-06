@echo off
REM ============================================================================
REM Build Script - Text2SQL Service
REM AI-Assistant Project
REM ============================================================================
REM Description: Automated build script with dependency validation and testing
REM Author: SkastVnT
REM Version: 1.0.0
REM ============================================================================

setlocal enabledelayedexpansion

REM Colors for output (Windows 10+)
set "GREEN=[92m"
set "RED=[91m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "RESET=[0m"

REM Script configuration
set "SERVICE_NAME=Text2SQL"
set "VENV_NAME=Text2SQL"
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

REM Check google-generativeai
python -c "import google.generativeai" >nul 2>&1
if errorlevel 1 (
    echo %RED%[FAIL]%RESET% google-generativeai
    set CRITICAL_FAILED=1
) else (
    echo %GREEN%[OK]%RESET% google-generativeai
)

REM Check pandas
python -c "import pandas; print(pandas.__version__)" >nul 2>&1
if errorlevel 1 (
    echo %RED%[FAIL]%RESET% pandas
    set CRITICAL_FAILED=1
) else (
    for /f "tokens=1" %%v in ('python -c "import pandas; print(pandas.__version__)" 2^>^&1') do echo %GREEN%[OK]%RESET% pandas %%v
)

REM Check clickhouse-connect
python -c "import clickhouse_connect" >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%[WARN]%RESET% clickhouse-connect (optional)
) else (
    echo %GREEN%[OK]%RESET% clickhouse-connect
)

REM Check pymongo
python -c "import pymongo" >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%[WARN]%RESET% pymongo (optional)
) else (
    echo %GREEN%[OK]%RESET% pymongo
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
REM STEP 8: Check Data Directories
REM ============================================================================
echo %YELLOW%[BONUS]%RESET% Checking directories...

if not exist "data" (
    echo %YELLOW%[INFO]%RESET% Creating data directory...
    mkdir data
    mkdir data\knowledge_base
    mkdir data\schemas
    echo %GREEN%[OK]%RESET% Data directories created
) else (
    echo %GREEN%[OK]%RESET% Data directory exists
)

if not exist "uploads" (
    echo %YELLOW%[INFO]%RESET% Creating uploads directory...
    mkdir uploads
    echo %GREEN%[OK]%RESET% Uploads directory created
) else (
    echo %GREEN%[OK]%RESET% Uploads directory exists
)

echo.

REM ============================================================================
REM STEP 9: Check .env Configuration
REM ============================================================================
echo %YELLOW%[CONFIG]%RESET% Checking configuration...

if not exist ".env" (
    echo %YELLOW%[WARN]%RESET% .env file not found
    echo.
    echo Required API keys:
    echo - GEMINI_API_KEY_1 (primary)
    echo - GEMINI_API_KEY_2 (optional, fallback)
    echo.
    echo Create .env file with:
    echo GEMINI_API_KEY_1=your_gemini_api_key
    echo.
) else (
    echo %GREEN%[OK]%RESET% .env file exists
    
    REM Check for Gemini API key
    findstr /i "GEMINI_API_KEY" .env >nul 2>&1
    if errorlevel 1 (
        echo %YELLOW%[WARN]%RESET% No Gemini API key found in .env
    ) else (
        echo %GREEN%[OK]%RESET% Gemini API key configured
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
echo 1. Configure .env file with Gemini API key (if not done)
echo 2. Run the service: python app_simple.py
echo 3. Access at: http://localhost:5002
echo.
echo For troubleshooting, see: BUILD_GUIDE.md
echo.

pause
