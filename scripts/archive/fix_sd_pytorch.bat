@echo off
echo ================================================================
echo   FIX STABLE DIFFUSION PYTORCH AND DEPENDENCIES
echo   - Reinstall PyTorch with CUDA support
echo   - Remove conflicting ldm package  
echo   - Fix xformers compatibility
echo ================================================================
echo.

echo CURRENT SYSTEM:
echo   GPU: NVIDIA GeForce RTX 3060 Ti (8GB VRAM)
echo   CUDA: 13.0 (Driver 581.57)
echo   Python: 3.10.11
echo.

echo ISSUE DETECTED:
echo   - PyTorch 2.8.0+cpu (CPU-only, no CUDA support)
echo   - Conflicting ldm package (face recognition library)
echo   - xformers incompatible with CPU-only PyTorch
echo.

echo FIX PLAN:
echo   1. Remove CPU-only PyTorch
echo   2. Install PyTorch 2.4.0 with CUDA 12.1
echo   3. Reinstall xformers compatible with PyTorch 2.4.0+cu121
echo   4. Remove conflicting ldm package
echo   5. Verify installation
echo.
pause

cd /d "I:\AI-Assistant\stable-diffusion-webui"

echo.
echo ================================================================
echo [1/6] Removing conflicting ldm package...
echo ================================================================
call venv_sd\Scripts\activate.bat
pip uninstall ldm -y

echo.
echo ================================================================
echo [2/6] Uninstalling CPU-only PyTorch...
echo ================================================================
pip uninstall torch torchvision torchaudio xformers -y

echo.
echo ================================================================
echo [3/6] Installing PyTorch 2.4.0 with CUDA 12.1...
echo ================================================================
echo This may take several minutes...
pip install torch==2.4.0+cu121 torchvision==0.19.0+cu121 torchaudio==2.4.0+cu121 --index-url https://download.pytorch.org/whl/cu121

echo.
echo ================================================================
echo [4/6] Installing xformers for PyTorch 2.4.0+cu121...
echo ================================================================
pip install xformers==0.0.27.post2 --index-url https://download.pytorch.org/whl/cu121

echo.
echo ================================================================
echo [5/6] Ensuring NumPy 1.x compatibility...
echo ================================================================
pip install "numpy<2.0" --force-reinstall

echo.
echo ================================================================
echo [6/6] Verifying installation...
echo ================================================================
python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA Available:', torch.cuda.is_available()); print('CUDA Version:', torch.version.cuda if torch.cuda.is_available() else 'N/A'); print('GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"

echo.
python -c "try: import xformers; print('xformers:', xformers.__version__, '- OK'); except Exception as e: print('xformers: NOT INSTALLED -', e)"

echo.
python -c "import numpy; print('NumPy:', numpy.__version__)"

echo.
echo ================================================================
echo   INSTALLATION COMPLETE!
echo ================================================================
echo.
echo Next steps:
echo   1. Test Stable Diffusion:
echo      python webui.py --api --xformers
echo.
echo   2. If successful, the WebUI will be available at:
echo      http://127.0.0.1:7860
echo.
pause
