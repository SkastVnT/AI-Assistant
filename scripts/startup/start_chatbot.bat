@echo off
echo ================================================================
echo   AI ASSISTANT - CHATBOT + STABLE DIFFUSION AUTO START
echo ================================================================
echo.

cd /d i:\AI-Assistant

REM Check if .env exists
if not exist .env (
    echo [ERROR] File .env khong ton tai!
    echo Vui long tao file .env tu .env.example va them API keys.
    echo.
    pause
    exit /b 1
)

if not exist ChatBot\.env (
    echo [ERROR] File ChatBot\.env khong ton tai!
    echo Vui long tao file ChatBot\.env tu ChatBot\.env.example va them API keys.
    echo.
    pause
    exit /b 1
)

echo [OK] File .env da ton tai
echo.
echo KHOI DONG THU TU:
echo 1. Stable Diffusion API (Terminal 1) - Port 7860
echo 2. ChatBot WebUI (Terminal hien tai) - Port 5000
echo.
echo Vui long doi Stable Diffusion khoi dong xong (khoang 30-60 giay)
echo truoc khi su dung tinh nang tao anh!
echo.
echo ================================================================
echo.

REM Start Stable Diffusion in background window
echo [1/2] Dang khoi dong Stable Diffusion API (Terminal rieng)...
start "Stable Diffusion API - Port 7860" cmd /k "cd /d i:\AI-Assistant\stable-diffusion-webui && echo Dang khoi dong Stable Diffusion API... && python webui.py --api --xformers --no-half-vae --disable-safe-unpickle --skip-prepare-environment --skip-version-check --skip-torch-cuda-test"

echo Doi 5 giay de SD khoi tao...
timeout /t 5 /nobreak > nul

echo.
echo [2/2] Dang khoi dong ChatBot...
echo Sau khi khoi dong, mo trinh duyet: http://127.0.0.1:5000
echo.
echo Nhan Ctrl+C de dung ChatBot (SD se tiep tuc chay o terminal khac)
echo ================================================================
echo.

cd ChatBot
python app.py
