@echo off
REM ============================================================================
REM Build Script - Speech2Text Service (VistralS2T)
REM AI-Assistant Project
REM ============================================================================
REM Description: Automated build script with AI model setup and CUDA validation
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
set "SERVICE_NAME=Speech2Text (VistralS2T)"
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
echo %YELLOW%[STEP 1/9]%RESET% Checking Python installation...

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
REM STEP 2: Check CUDA (Optional but Recommended)
REM ============================================================================
echo %YELLOW%[STEP 2/9]%RESET% Checking CUDA availability...

nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%[WARN]%RESET% NVIDIA GPU not detected or nvidia-smi not in PATH
    echo %YELLOW%[INFO]%RESET% Service will run in CPU mode (slower)
    set "CUDA_AVAILABLE=0"
) else (
    echo %GREEN%[OK]%RESET% NVIDIA GPU detected
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
    set "CUDA_AVAILABLE=1"
)

echo.

REM ============================================================================
REM STEP 3: Check/Create Virtual Environment
REM ============================================================================
echo %YELLOW%[STEP 3/9]%RESET% Checking virtual environment...

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
REM STEP 4: Activate Virtual Environment
REM ============================================================================
echo %YELLOW%[STEP 4/9]%RESET% Activating virtual environment...

call %VENV_NAME%\Scripts\activate.bat
if errorlevel 1 (
    echo %RED%[ERROR]%RESET% Failed to activate virtual environment!
    pause
    exit /b 1
)

echo %GREEN%[OK]%RESET% Virtual environment activated
echo.

REM ============================================================================
REM STEP 5: Upgrade pip
REM ============================================================================
echo %YELLOW%[STEP 5/9]%RESET% Upgrading pip...

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
REM STEP 6: Install PyTorch First (Critical)
REM ============================================================================
echo %YELLOW%[STEP 6/9]%RESET% Checking PyTorch...

python -c "import torch" >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%[INFO]%RESET% PyTorch not installed, installing...
    echo.
    
    if "%CUDA_AVAILABLE%"=="1" (
        echo Installing PyTorch with CUDA support...
        pip install torch==2.0.1 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118
    ) else (
        echo Installing PyTorch CPU-only version...
        pip install torch==2.0.1 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cpu
    )
    
    if errorlevel 1 (
        echo %RED%[ERROR]%RESET% Failed to install PyTorch!
        pause
        exit /b 1
    )
    
    echo %GREEN%[OK]%RESET% PyTorch installed
) else (
    for /f "tokens=1" %%v in ('python -c "import torch; print(torch.__version__)" 2^>^&1') do echo %GREEN%[OK]%RESET% PyTorch %%v already installed
    
    REM Check CUDA
    python -c "import torch; print('CUDA available:', torch.cuda.is_available())" 2>&1
)

echo.

REM ============================================================================
REM STEP 7: Install/Check Dependencies
REM ============================================================================
echo %YELLOW%[STEP 7/9]%RESET% Checking dependencies from %REQUIREMENTS_FILE%...

if not exist "%REQUIREMENTS_FILE%" (
    echo %RED%[ERROR]%RESET% %REQUIREMENTS_FILE% not found!
    pause
    exit /b 1
)

echo.
echo %YELLOW%[INFO]%RESET% Installing dependencies (this may take 5-10 minutes)...
echo.

pip install -r %REQUIREMENTS_FILE%
if errorlevel 1 (
    echo.
    echo %RED%[ERROR]%RESET% Failed to install some dependencies!
    echo.
    echo Common issues:
    echo - pyannote.audio: Requires HuggingFace token
    echo - librosa: May need Visual C++ Build Tools
    echo.
    echo See BUILD_GUIDE.md for detailed troubleshooting
    pause
    exit /b 1
)

echo.
echo %GREEN%[OK]%RESET% All dependencies installed successfully
echo.

REM ============================================================================
REM STEP 8: Verify Critical Packages
REM ============================================================================
echo %YELLOW%[STEP 8/9]%RESET% Verifying critical packages...

set CRITICAL_FAILED=0

REM Check faster-whisper
python -c "import faster_whisper" >nul 2>&1
if errorlevel 1 (
    echo %RED%[FAIL]%RESET% faster-whisper
    set CRITICAL_FAILED=1
) else (
    echo %GREEN%[OK]%RESET% faster-whisper
)

REM Check transformers
python -c "import transformers; print(transformers.__version__)" >nul 2>&1
if errorlevel 1 (
    echo %RED%[FAIL]%RESET% transformers
    set CRITICAL_FAILED=1
) else (
    for /f "tokens=1" %%v in ('python -c "import transformers; print(transformers.__version__)" 2^>^&1') do echo %GREEN%[OK]%RESET% transformers %%v
)

REM Check pyannote.audio
python -c "import pyannote.audio" >nul 2>&1
if errorlevel 1 (
    echo %RED%[FAIL]%RESET% pyannote.audio
    echo %YELLOW%[INFO]%RESET% May need HF_TOKEN for speaker diarization
    set CRITICAL_FAILED=1
) else (
    echo %GREEN%[OK]%RESET% pyannote.audio
)

REM Check librosa
python -c "import librosa; print(librosa.__version__)" >nul 2>&1
if errorlevel 1 (
    echo %RED%[FAIL]%RESET% librosa
    set CRITICAL_FAILED=1
) else (
    for /f "tokens=1" %%v in ('python -c "import librosa; print(librosa.__version__)" 2^>^&1') do echo %GREEN%[OK]%RESET% librosa %%v
)

REM Check soundfile
python -c "import soundfile" >nul 2>&1
if errorlevel 1 (
    echo %RED%[FAIL]%RESET% soundfile
    set CRITICAL_FAILED=1
) else (
    echo %GREEN%[OK]%RESET% soundfile
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
REM STEP 9: Check Directories & Configuration
REM ============================================================================
echo %YELLOW%[STEP 9/9]%RESET% Checking directories...

if not exist "results" (
    echo %YELLOW%[INFO]%RESET% Creating results directory...
    mkdir results
    echo %GREEN%[OK]%RESET% Results directory created
) else (
    echo %GREEN%[OK]%RESET% Results directory exists
)

if not exist "logs" (
    echo %YELLOW%[INFO]%RESET% Creating logs directory...
    mkdir logs
    echo %GREEN%[OK]%RESET% Logs directory created
) else (
    echo %GREEN%[OK]%RESET% Logs directory exists
)

if not exist "data\audio" (
    echo %YELLOW%[INFO]%RESET% Creating data\audio directory...
    mkdir data\audio
    echo %GREEN%[OK]%RESET% Audio directory created
) else (
    echo %GREEN%[OK]%RESET% Audio directory exists
)

echo.

REM ============================================================================
REM STEP 10: Check .env & HuggingFace Token
REM ============================================================================
echo %YELLOW%[CONFIG]%RESET% Checking configuration...

if not exist ".env" (
    echo %YELLOW%[WARN]%RESET% .env file not found
    echo.
    echo Required for speaker diarization:
    echo - HF_TOKEN (from https://huggingface.co/settings/tokens)
    echo.
    echo Create .env file with:
    echo HF_TOKEN=your_huggingface_token
    echo.
    echo You must also accept licenses at:
    echo https://huggingface.co/pyannote/speaker-diarization-3.1
    echo https://huggingface.co/pyannote/segmentation-3.0
    echo.
) else (
    echo %GREEN%[OK]%RESET% .env file exists
    
    REM Check for HF token
    findstr /i "HF_TOKEN" .env >nul 2>&1
    if errorlevel 1 (
        echo %YELLOW%[WARN]%RESET% No HF_TOKEN found in .env
        echo %YELLOW%[INFO]%RESET% Speaker diarization will not work without it
    ) else (
        echo %GREEN%[OK]%RESET% HF_TOKEN configured
    )
)

echo.

REM ============================================================================
REM MODEL DOWNLOAD INFO
REM ============================================================================
echo %YELLOW%[INFO]%RESET% AI Models Information:
echo.
echo Models will auto-download on first run (~5GB total):
echo   - Whisper Large-v3 (~3GB)
echo   - PhoWhisper base (~1GB)
echo   - Qwen2.5-1.5B-Instruct (~3GB)
echo   - pyannote diarization (~500MB)
echo.
echo %YELLOW%[TIP]%RESET% Use CUDA for 5-10x faster processing!
echo.

REM ============================================================================
REM BUILD COMPLETE
REM ============================================================================
echo %GREEN%============================================================%RESET%
echo %GREEN%  BUILD COMPLETE - %SERVICE_NAME% SERVICE%RESET%
echo %GREEN%============================================================%RESET%
echo.
echo Next steps:
echo 1. Configure .env file with HF_TOKEN (if not done)
echo 2. Accept pyannote licenses on HuggingFace
echo 3. Run the service: start_webui.bat
echo 4. Access WebUI at: http://localhost:7860
echo.
echo For troubleshooting, see: BUILD_GUIDE.md
echo.

pause
