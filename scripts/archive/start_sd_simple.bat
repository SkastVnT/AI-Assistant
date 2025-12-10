@echo off
echo ============================================
echo   STABLE DIFFUSION - SIMPLE START
echo   (Bypass installation errors)
echo ============================================
echo.

cd i:\AI-Assistant\stable-diffusion-webui

echo Dang khoi dong Stable Diffusion voi API enabled...
echo Su dung webui.bat co san de tranh conflict...
echo.
echo API URL: http://127.0.0.1:7860
echo WebUI: http://127.0.0.1:7860
echo.
echo Sau khi khoi dong xong, mo ChatBot:
echo http://127.0.0.1:5000
echo ============================================
echo.

REM Sử dụng webui.bat có sẵn với commandline args
call webui.bat --api --xformers --no-half-vae --disable-safe-unpickle

pause
