@echo off
REM ============================================================================
REM Build Script - Document Intelligence Service
REM AI-Assistant Project
REM ============================================================================
REM Description: Automated build script with OCR & AI setup validation
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
set "SERVICE_NAME=Document Intelligence"
set "VENV_NAME=venv"
set "PYTHON_VERSION=3.10"
set "REQUIREMENTS_FILE=requirements.txt"

echo.
echo %BLUE%============================================================%RESET%
echo %BLUE%  BUILD SCRIPT - %SERVICE_NAME% SERVICE%RESET%
echo %BLUE%============================================================%RESET%
echo.

REM ============================================================================
REM STEP 1: Check Python Installation
REM ============================================================================
echo %YELLOW%[STEP 1/8]%RESET% Checking Python installation...

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
echo %YELLOW%[STEP 2/8]%RESET% Checking virtual environment...

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
echo %YELLOW%[STEP 3/8]%RESET% Activating virtual environment...

call %VENV_NAME%\Scripts\activate.bat
if errorlevel 1 (
    echo %RED%[ERROR]%RESET% Failed to activate virtual environment!
    pause
    exit /b 1
)

echo %GREEN%[OK]%RESET% Virtual environment activated
echo.

REM ============================================================================
REM STEP 4: Set Critical Environment Variable
REM ============================================================================
echo %YELLOW%[STEP 4/8]%RESET% Setting PaddlePaddle environment...

REM CRITICAL: PaddlePaddle requires this for protobuf compatibility
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
echo %GREEN%[OK]%RESET% PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

echo.

REM ============================================================================
REM STEP 5: Upgrade pip
REM ============================================================================
echo %YELLOW%[STEP 5/8]%RESET% Upgrading pip...

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
REM STEP 6: Install/Check Dependencies
REM ============================================================================
echo %YELLOW%[STEP 6/8]%RESET% Checking dependencies from %REQUIREMENTS_FILE%...

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
    
    REM Install protobuf first (critical for PaddlePaddle)
    echo Installing protobuf 3.20.2 (PaddlePaddle compatibility)...
    pip install protobuf==3.20.2
    
    echo.
    echo Installing remaining packages...
    pip install -r %REQUIREMENTS_FILE%
    if errorlevel 1 (
        echo.
        echo %RED%[ERROR]%RESET% Failed to install some dependencies!
        echo.
        echo Common issues:
        echo - opencv-python: May require Visual C++ Redistributable
        echo - paddlepaddle: Windows may need specific version
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
REM STEP 7: Verify Critical Packages
REM ============================================================================
echo %YELLOW%[STEP 7/8]%RESET% Verifying critical packages...

set CRITICAL_FAILED=0

REM Check Flask
python -c "import flask; print('Flask:', flask.__version__)" >nul 2>&1
if errorlevel 1 (
    echo %RED%[FAIL]%RESET% Flask
    set CRITICAL_FAILED=1
) else (
    for /f "tokens=2" %%v in ('python -c "import flask; print('Flask:', flask.__version__)" 2^>^&1') do echo %GREEN%[OK]%RESET% Flask %%v
)

REM Check PaddlePaddle
python -c "import paddle; print(paddle.__version__)" >nul 2>&1
if errorlevel 1 (
    echo %RED%[FAIL]%RESET% paddlepaddle
    set CRITICAL_FAILED=1
) else (
    for /f "tokens=1" %%v in ('python -c "import paddle; print(paddle.__version__)" 2^>^&1') do echo %GREEN%[OK]%RESET% paddlepaddle %%v
)

REM Check PaddleOCR
python -c "import paddleocr; print(paddleocr.__version__)" >nul 2>&1
if errorlevel 1 (
    echo %RED%[FAIL]%RESET% paddleocr
    set CRITICAL_FAILED=1
) else (
    for /f "tokens=1" %%v in ('python -c "import paddleocr; print(paddleocr.__version__)" 2^>^&1') do echo %GREEN%[OK]%RESET% paddleocr %%v
)

REM Check google-generativeai
python -c "import google.generativeai" >nul 2>&1
if errorlevel 1 (
    echo %RED%[FAIL]%RESET% google-generativeai
    set CRITICAL_FAILED=1
) else (
    echo %GREEN%[OK]%RESET% google-generativeai
)

REM Check Pillow
python -c "import PIL; print(PIL.__version__)" >nul 2>&1
if errorlevel 1 (
    echo %RED%[FAIL]%RESET% Pillow
    set CRITICAL_FAILED=1
) else (
    for /f "tokens=1" %%v in ('python -c "import PIL; print(PIL.__version__)" 2^>^&1') do echo %GREEN%[OK]%RESET% Pillow %%v
)

REM Check PyMuPDF (fitz)
python -c "import fitz; print(fitz.__version__)" >nul 2>&1
if errorlevel 1 (
    echo %RED%[FAIL]%RESET% PyMuPDF (fitz)
    set CRITICAL_FAILED=1
) else (
    for /f "tokens=1" %%v in ('python -c "import fitz; print(fitz.__version__)" 2^>^&1') do echo %GREEN%[OK]%RESET% PyMuPDF %%v
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
REM STEP 8: Check Directories
REM ============================================================================
echo %YELLOW%[STEP 8/8]%RESET% Checking directories...

if not exist "output" (
    echo %YELLOW%[INFO]%RESET% Creating output directory...
    mkdir output
    echo %GREEN%[OK]%RESET% Output directory created
) else (
    echo %GREEN%[OK]%RESET% Output directory exists
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
REM STEP 9: Download OCR Models
REM ============================================================================
echo %YELLOW%[BONUS]%RESET% Checking OCR models...

echo %YELLOW%[INFO]%RESET% PaddleOCR will auto-download models on first run
echo %YELLOW%[INFO]%RESET% Models required (~200MB):
echo   - detection model (ch_PP-OCRv4_det)
echo   - recognition model (ch_PP-OCRv4_rec)
echo   - classification model (ch_ppocr_mobile_v2.0_cls)
echo.

REM ============================================================================
REM STEP 10: Check .env Configuration
REM ============================================================================
echo %YELLOW%[CONFIG]%RESET% Checking configuration...

if not exist ".env" (
    echo %YELLOW%[WARN]%RESET% .env file not found
    echo.
    echo Required API keys:
    echo - GEMINI_API_KEY (for AI enhancement)
    echo.
    echo Create .env file with:
    echo GEMINI_API_KEY=your_gemini_api_key
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
echo IMPORTANT: Set this environment variable before running:
echo set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
echo.
echo Next steps:
echo 1. Configure .env file with Gemini API key (if not done)
echo 2. Run the service: start_service.bat (or python app.py)
echo 3. Access at: http://localhost:5003
echo.
echo For troubleshooting, see: BUILD_GUIDE.md
echo.

pause
