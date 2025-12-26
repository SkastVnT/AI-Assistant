@echo off
REM Fix Speech2Text dependencies - pyannote.audio compatibility
title Fixing Speech2Text Dependencies
color 0E

cd /d "%~dp0.."

echo ============================================================================
echo   Fixing Speech2Text Service Dependencies
echo ============================================================================
echo.
echo This will reinstall pyannote.audio with compatible versions for torchaudio 2.1.2
echo.

if not exist ".venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found
    pause
    exit /b 1
)

call .venv\Scripts\activate.bat

echo [1/4] Uninstalling incompatible packages...
pip uninstall -y pyannote.audio pyannote.core pyannote.database pyannote.metrics pyannote.pipeline speechbrain torch torchvision torchaudio >nul 2>&1

echo [2/4] Installing compatible PyTorch 2.1.2 with CUDA 11.8...
python -m pip install torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 --index-url https://download.pytorch.org/whl/cu118

echo [3/4] Installing pyannote.audio 3.1 compatible with PyTorch 2.1.2 and NumPy 1.x...
python -m pip install "numpy<2.0.0"
python -m pip install pyannote.audio==3.1.1 --no-deps
python -m pip install asteroid-filterbanks einops lightning huggingface-hub matplotlib pytorch-metric-learning rich safetensors speechbrain torch-audiomentations torchmetrics pyannote.core==5.0.0 pyannote.database==5.1.0 pyannote.metrics==3.2.1 pyannote.pipeline==3.0.1

echo [4/4] Installing additional audio processing libraries...
python -m pip install soundfile librosa pydub faster-whisper

echo.
echo ============================================================================
echo   ✅ Speech2Text Dependencies Fixed!
echo ============================================================================
echo.
echo You can now run the Speech2Text service.
echo.
pause
