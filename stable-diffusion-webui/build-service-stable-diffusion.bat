@echo off
REM ============================================================================
REM Build Script - Stable Diffusion Service (AUTOMATIC1111 WebUI)
REM AI-Assistant Project
REM ============================================================================
REM Description: Automated setup script for Stable Diffusion WebUI
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
set "SERVICE_NAME=Stable Diffusion (AUTOMATIC1111)"
set "PYTHON_VERSION=3.10"
set "WEBUI_SCRIPT=webui-user.bat"

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
REM STEP 2: Check CUDA (Required for GPU Acceleration)
REM ============================================================================
echo %YELLOW%[STEP 2/7]%RESET% Checking CUDA availability...

nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo %YELLOW%[WARN]%RESET% NVIDIA GPU not detected or nvidia-smi not in PATH
    echo.
    echo %YELLOW%[IMPORTANT]%RESET% Stable Diffusion REQUIRES NVIDIA GPU with CUDA!
    echo CPU-only mode is extremely slow (not recommended).
    echo.
    echo Minimum requirements:
    echo - NVIDIA GPU with 4GB+ VRAM (6GB+ recommended)
    echo - CUDA 11.8 or 12.1
    echo - Latest NVIDIA drivers
    echo.
    set "CUDA_AVAILABLE=0"
    
    choice /C YN /M "Continue anyway?"
    if errorlevel 2 exit /b 1
) else (
    echo %GREEN%[OK]%RESET% NVIDIA GPU detected:
    echo.
    nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
    echo.
    set "CUDA_AVAILABLE=1"
)

echo.

REM ============================================================================
REM STEP 3: Check Git Installation
REM ============================================================================
echo %YELLOW%[STEP 3/7]%RESET% Checking Git installation...

git --version >nul 2>&1
if errorlevel 1 (
    echo %RED%[ERROR]%RESET% Git is not installed!
    echo.
    echo Install Git from: https://git-scm.com/download/win
    echo.
    pause
    exit /b 1
)

for /f "tokens=3" %%i in ('git --version 2^>^&1') do set GIT_VER=%%i
echo %GREEN%[OK]%RESET% Git %GIT_VER% found

echo.

REM ============================================================================
REM STEP 4: Check/Initialize Repository
REM ============================================================================
echo %YELLOW%[STEP 4/7]%RESET% Checking repository...

if not exist ".git" (
    echo %YELLOW%[WARN]%RESET% Not a git repository
    echo %YELLOW%[INFO]%RESET% This directory should be the stable-diffusion-webui repository
    echo.
    echo If you haven't cloned the repository yet, run:
    echo git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
    echo.
    pause
    exit /b 1
) else (
    echo %GREEN%[OK]%RESET% Git repository detected
    
    REM Check remote origin
    for /f "tokens=*" %%r in ('git remote get-url origin 2^>^&1') do set REMOTE_URL=%%r
    echo %YELLOW%[INFO]%RESET% Remote: !REMOTE_URL!
)

echo.

REM ============================================================================
REM STEP 5: Check Essential Directories
REM ============================================================================
echo %YELLOW%[STEP 5/7]%RESET% Checking directories...

set MISSING_DIRS=0

if not exist "models\Stable-diffusion" (
    echo %YELLOW%[INFO]%RESET% Creating models\Stable-diffusion directory...
    mkdir "models\Stable-diffusion"
    set MISSING_DIRS=1
) else (
    echo %GREEN%[OK]%RESET% models\Stable-diffusion exists
)

if not exist "models\Lora" (
    echo %YELLOW%[INFO]%RESET% Creating models\Lora directory...
    mkdir "models\Lora"
) else (
    echo %GREEN%[OK]%RESET% models\Lora exists
)

if not exist "models\VAE" (
    echo %YELLOW%[INFO]%RESET% Creating models\VAE directory...
    mkdir "models\VAE"
) else (
    echo %GREEN%[OK]%RESET% models\VAE exists
)

if not exist "embeddings" (
    echo %YELLOW%[INFO]%RESET% Creating embeddings directory...
    mkdir "embeddings"
) else (
    echo %GREEN%[OK]%RESET% embeddings exists
)

echo.

REM ============================================================================
REM STEP 6: Check for Stable Diffusion Models
REM ============================================================================
echo %YELLOW%[STEP 6/7]%RESET% Checking Stable Diffusion models...

set MODEL_COUNT=0
for %%f in ("models\Stable-diffusion\*.safetensors" "models\Stable-diffusion\*.ckpt") do (
    set /a MODEL_COUNT+=1
)

if %MODEL_COUNT% EQU 0 (
    echo %YELLOW%[WARN]%RESET% No Stable Diffusion models found!
    echo.
    echo %YELLOW%[INFO]%RESET% You need to download at least one model:
    echo.
    echo Recommended models (~2-7GB each):
    echo 1. Stable Diffusion 1.5
    echo    https://huggingface.co/runwayml/stable-diffusion-v1-5
    echo.
    echo 2. Stable Diffusion XL 1.0
    echo    https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0
    echo.
    echo 3. Anime models (e.g., Anything V5, CounterfeitXL)
    echo    https://civitai.com/
    echo.
    echo Place .safetensors or .ckpt files in: models\Stable-diffusion\
    echo.
) else (
    echo %GREEN%[OK]%RESET% Found %MODEL_COUNT% model(s):
    for %%f in ("models\Stable-diffusion\*.safetensors" "models\Stable-diffusion\*.ckpt") do (
        echo   - %%~nxf
    )
)

echo.

REM ============================================================================
REM STEP 7: Check webui-user.bat Configuration
REM ============================================================================
echo %YELLOW%[STEP 7/7]%RESET% Checking %WEBUI_SCRIPT%...

if not exist "%WEBUI_SCRIPT%" (
    echo %RED%[ERROR]%RESET% %WEBUI_SCRIPT% not found!
    echo.
    echo This file should exist in stable-diffusion-webui root.
    echo Please ensure you're in the correct directory.
    pause
    exit /b 1
) else (
    echo %GREEN%[OK]%RESET% %WEBUI_SCRIPT% found
    
    REM Check if xformers is configured
    findstr /i "xformers" %WEBUI_SCRIPT% >nul 2>&1
    if errorlevel 1 (
        echo %YELLOW%[INFO]%RESET% xformers not configured (recommended for faster generation)
    ) else (
        echo %GREEN%[OK]%RESET% xformers configured
    )
)

echo.

REM ============================================================================
REM RECOMMENDED SETTINGS
REM ============================================================================
echo %YELLOW%[TIPS]%RESET% Recommended settings for %WEBUI_SCRIPT%:
echo.
echo Add these lines to enable optimizations:
echo   set COMMANDLINE_ARGS=--xformers --opt-sdp-attention --api
echo.
echo Flags explained:
echo   --xformers             : Faster generation (NVIDIA only)
echo   --opt-sdp-attention    : Memory optimization
echo   --api                  : Enable REST API for integration
echo   --listen               : Allow external connections
echo   --port 7861            : Custom port
echo.

REM ============================================================================
REM VENV CHECK
REM ============================================================================
echo %YELLOW%[INFO]%RESET% Virtual environment status:

if exist "venv\Scripts\python.exe" (
    echo %GREEN%[OK]%RESET% Virtual environment exists (created by webui.bat)
) else (
    echo %YELLOW%[INFO]%RESET% Virtual environment will be created on first run
    echo %YELLOW%[INFO]%RESET% This process may take 10-20 minutes
    echo %YELLOW%[INFO]%RESET% Required downloads: ~4GB (PyTorch, dependencies)
)

echo.

REM ============================================================================
REM BUILD COMPLETE
REM ============================================================================
echo %GREEN%============================================================%RESET%
echo %GREEN%  BUILD COMPLETE - %SERVICE_NAME% SERVICE%RESET%
echo %GREEN%============================================================%RESET%
echo.
echo System ready! To start Stable Diffusion:
echo.
echo 1. Download at least one SD model (if not done)
echo 2. Run: webui-user.bat (or webui.bat)
echo 3. Wait for initial setup (10-20 min on first run)
echo 4. Access WebUI at: http://localhost:7860
echo.
echo For ChatBot integration:
echo - API will be available at: http://localhost:7860/sdapi/v1
echo - Make sure to add --api flag in webui-user.bat
echo.
echo %YELLOW%[PERFORMANCE TIPS]%RESET%
echo - Enable xformers for 20-30%% speed boost
echo - Use --medvram if you have 4-6GB VRAM
echo - Use --lowvram if you have less than 4GB VRAM
echo.
echo For troubleshooting, see: BUILD_GUIDE.md
echo.

pause
