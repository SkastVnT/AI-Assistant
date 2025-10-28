@echo off
echo ============================================
echo   INSTALL PYTORCH WITH CUDA 11.8
echo ============================================
echo.
echo GPU: RTX 3060 Ti
echo CUDA Driver: 13.0 (supports CUDA 11.8)
echo.
echo This will:
echo 1. Uninstall CPU-only PyTorch
echo 2. Install PyTorch with CUDA 11.8 support
echo.
echo WARNING: This may take 5-10 minutes!
echo ============================================
echo.
pause

echo.
echo [1/2] Uninstalling CPU-only PyTorch...
pip uninstall -y torch torchvision torchaudio

echo.
echo [2/2] Installing PyTorch with CUDA 11.8...
pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118

echo.
echo ============================================
echo   INSTALLATION COMPLETE!
echo ============================================
echo.
echo Testing CUDA...
python -c "import torch; print('PyTorch version:', torch.__version__); print('CUDA available:', torch.cuda.is_available()); print('CUDA device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A')"

echo.
echo Now restart Stable Diffusion WITHOUT CPU flags!
echo.
pause
