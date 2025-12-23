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
REM Detect GPU and determine PyTorch installation type
REM ============================================================================
echo [INFO] Detecting GPU capabilities...
echo.

set HAS_NVIDIA_GPU=0
set CUDA_VERSION=none
set PYTORCH_INDEX_URL=

REM Check if nvidia-smi exists (NVIDIA GPU present)
nvidia-smi >nul 2>&1
if not errorlevel 1 (
    echo [OK] NVIDIA GPU detected
    set HAS_NVIDIA_GPU=1
    
    REM Try to detect CUDA version
    nvcc --version >nul 2>&1
    if not errorlevel 1 (
        for /f "tokens=5" %%v in ('nvcc --version ^| findstr "release"') do set CUDA_VERSION=%%v
        echo [OK] CUDA !CUDA_VERSION! detected
    ) else (
        echo [WARNING] CUDA toolkit not found, but GPU is present
        echo [INFO] Will install CUDA 11.8 compatible PyTorch
    )
    
    REM Set PyTorch installation URL for CUDA 11.8
    set PYTORCH_INDEX_URL=--index-url https://download.pytorch.org/whl/cu118
    echo [INFO] Will install PyTorch with CUDA 11.8 support
) else (
    echo [INFO] No NVIDIA GPU detected
    echo [INFO] Will install CPU-only PyTorch
)
echo.

REM ============================================================================
REM Check for missing critical packages
REM ============================================================================
echo [INFO] Checking installed packages...
echo.

set NEED_INSTALL=0
set NEED_PYTORCH=0

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
    set NEED_PYTORCH=1
) else (
    REM Check if PyTorch has CUDA support when GPU is present
    if !HAS_NVIDIA_GPU! EQU 1 (
        python -c "import torch; exit(0 if torch.cuda.is_available() else 1)" >nul 2>&1
        if errorlevel 1 (
            echo [WARNING] PyTorch installed but CUDA not available
            echo [INFO] Will reinstall PyTorch with CUDA support
            set NEED_PYTORCH=1
            set NEED_INSTALL=1
        ) else (
            echo [OK] PyTorch with CUDA support found
        )
    ) else (
        echo [OK] PyTorch (CPU) found
    )
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
    
    REM Install PyTorch first if needed (CRITICAL for other ML packages)
    if !NEED_PYTORCH! EQU 1 (
        echo ============================================================================
        echo   Installing PyTorch (Most Important Step)
        echo ============================================================================
        echo.
        
        if !HAS_NVIDIA_GPU! EQU 1 (
            echo [Step 1/2] Uninstalling old PyTorch versions...
            pip uninstall -y torch torchvision torchaudio >nul 2>&1
            
            echo [Step 2/2] Installing PyTorch 2.6.0 with CUDA 11.8 support...
            echo [INFO] This may take 5-15 minutes depending on internet speed...
            echo.
            python -m pip install torch==2.6.0 torchvision==0.16.2 torchaudio==2.1.2 !PYTORCH_INDEX_URL! --disable-pip-version-check
            
            if errorlevel 1 (
                echo.
                echo [ERROR] Failed to install PyTorch with CUDA
                echo [INFO] Trying CPU-only version as fallback...
                python -m pip install torch==2.6.0 torchvision==0.16.2 torchaudio==2.1.2 --disable-pip-version-check
                
                if errorlevel 1 (
                    echo [ERROR] Failed to install PyTorch!
                    echo [ERROR] Please check your internet connection
                    pause
                    exit /b 1
                ) else (
                    echo [WARNING] Installed CPU-only PyTorch (no GPU acceleration)
                )
            ) else (
                echo.
                echo [SUCCESS] PyTorch with CUDA 11.8 installed successfully!
                echo [INFO] GPU acceleration enabled for:
                echo   - Stable Diffusion (10-20x faster)
                echo   - Image Upscale (5-10x faster)
                echo   - LoRA Training (required)
                echo   - Speech2Text (3-5x faster)
            )
        ) else (
            echo [INFO] Installing CPU-only PyTorch...
            python -m pip install torch==2.6.0 torchvision==0.16.2 torchaudio==2.1.2 --disable-pip-version-check
            
            if errorlevel 1 (
                echo [ERROR] Failed to install PyTorch!
                pause
                exit /b 1
            ) else (
                echo [OK] PyTorch (CPU-only) installed
            )
        )
        echo.
    )
    
    REM Try requirements.txt first, but don't fail if it errors
    echo [Step 1/2] Attempting to install from requirements.txt...
    pip install -r requirements.txt 2>nul
    
    REM Install critical packages individually
    echo.
    echo [Step 2/2] Installing critical packages individually...
    echo.
    
    echo   [1/7] Flask web framework...
    python -m pip install flask flask-cors python-dotenv werkzeug --disable-pip-version-check
    
    echo   [2/7] Database drivers...
    python -m pip install pymongo dnspython redis --disable-pip-version-check
    
    echo   [3/7] NumPy...
    python -m pip install "numpy<2.0.0" --disable-pip-version-check
    
    echo   [4/7] AI/ML transformers...
    python -m pip install transformers accelerate sentencepiece protobuf --disable-pip-version-check
    
    echo   [5/7] Semantic search...
    python -m pip install sentence-transformers scipy scikit-learn --disable-pip-version-check
    
    echo   [6/7] AI APIs...
    python -m pip install google-genai openai --disable-pip-version-check
    
    echo   [7/7] Gradio UI and utilities...
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
