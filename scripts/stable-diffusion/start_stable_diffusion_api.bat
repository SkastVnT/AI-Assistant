@echo off
echo ============================================
echo   STABLE DIFFUSION WEBUI - API MODE
echo ============================================
echo.
echo Dang khoi dong Stable Diffusion voi API enabled...
echo API URL: http://127.0.0.1:7860
echo.
echo Sau khi khoi dong xong, mo ChatBot de tao anh!
echo ============================================
echo.

cd i:\AI-Assistant\stable-diffusion-webui

REM Khởi động với các flags cho GPU (CUDA):
REM --api: Enable API
REM --xformers: Tối ưu VRAM với xFormers (CUDA only)
REM --no-half-vae: Tránh lỗi black images
REM --medvram: Tối ưu cho GPU 8GB (RTX 3060 Ti)
REM --disable-safe-unpickle: Cho phép load mọi checkpoint

python webui.py --api --xformers --no-half-vae --medvram --disable-safe-unpickle --skip-prepare-environment --skip-version-check

pause
