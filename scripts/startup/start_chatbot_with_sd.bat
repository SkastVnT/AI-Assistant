@echo off
echo ================================================================
echo   AI ASSISTANT - CHATBOT + STABLE DIFFUSION AUTO START
echo ================================================================
echo.

REM Check if .env exists
if not exist i:\AI-Assistant\.env (
    echo [ERROR] File .env khong ton tai!
    echo Vui long tao file .env tu .env.example va them API keys.
    echo.
    pause
    exit /b 1
)

if not exist i:\AI-Assistant\ChatBot\.env (
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
echo 2. ChatBot WebUI (Terminal 2) - Port 5000
echo.
echo Vui long doi Stable Diffusion khoi dong xong (khoang 30-60 giay)
echo truoc khi su dung tinh nang tao anh!
echo.
echo ================================================================
echo.

REM Start Stable Diffusion in new window
echo [1/2] Dang khoi dong Stable Diffusion API...
start "Stable Diffusion API" cmd /k "cd /d i:\AI-Assistant\stable-diffusion-webui && python webui.py --api --xformers --no-half-vae --disable-safe-unpickle --skip-prepare-environment --skip-version-check --skip-torch-cuda-test"

echo Doi 5 giay truoc khi khoi dong ChatBot...
timeout /t 5 /nobreak > nul

REM Start ChatBot in new window
echo [2/2] Dang khoi dong ChatBot...
start "ChatBot WebUI" cmd /k "cd /d i:\AI-Assistant\ChatBot && python app.py"

echo.
echo ================================================================
echo   HOAN THANH!
echo ================================================================
echo.
echo Da khoi dong 2 terminal:
echo   - Terminal 1: Stable Diffusion API (http://127.0.0.1:7860)
echo   - Terminal 2: ChatBot WebUI (http://127.0.0.1:5000)
echo.
echo Mo trinh duyet: http://127.0.0.1:5000
echo.
echo De DUNG dich vu: Dong tung terminal hoac nhan Ctrl+C
echo.
pause
