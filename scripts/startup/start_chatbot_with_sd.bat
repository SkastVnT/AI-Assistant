@echo off
echo ================================================================
echo   AI ASSISTANT - CHATBOT + STABLE DIFFUSION AUTO START
echo ================================================================
echo.

REM Check if .env exists (optional - show warning but continue)
if not exist i:\AI-Assistant\.env (
    echo [WARNING] File .env khong ton tai - se su dung gia tri mac dinh
    echo Ban co the tao file .env tu .env.example neu can API keys.
    echo.
) else (
    echo [OK] File .env da ton tai
)

if not exist i:\AI-Assistant\ChatBot\.env (
    echo [WARNING] File ChatBot\.env khong ton tai - se su dung gia tri mac dinh
    echo Ban co the tao file ChatBot\.env tu ChatBot\.env.example neu can API keys.
    echo.
) else (
    echo [OK] File ChatBot\.env da ton tai
)

echo Tiep tuc khoi dong...
echo.

REM Check if venv_sd exists
if not exist i:\AI-Assistant\stable-diffusion-webui\venv_sd (
    echo [ERROR] Virtual environment venv_sd khong ton tai!
    echo Vui long chay setup script truoc:
    echo   cd stable-diffusion-webui
    echo   setup_venv_sd.bat
    echo.
    pause
    exit /b 1
)

REM Check if venv_chatbot exists
if not exist i:\AI-Assistant\ChatBot\venv_chatbot (
    echo [ERROR] Virtual environment venv_chatbot khong ton tai!
    echo Vui long chay setup script truoc:
    echo   cd ChatBot
    echo   setup_venv_chatbot.bat
    echo.
    pause
    exit /b 1
)

echo [OK] Ca hai virtual environments da ton tai
echo.
echo KHOI DONG THU TU:
echo 1. Stable Diffusion API (venv_sd) - Port 7860 - PyTorch 2.0.1
echo 2. ChatBot WebUI (venv_chatbot) - Port 5000 - PyTorch 2.4.0
echo.
echo MOI TRUONG RIENG BIET:
echo - SD WebUI: PyTorch 2.0.1 + torchvision 0.15.2 + xformers 0.0.20
echo - ChatBot: PyTorch 2.4.0 + transformers + local models support
echo.
echo Vui long doi Stable Diffusion khoi dong xong (khoang 30-60 giay)
echo truoc khi su dung tinh nang tao anh!
echo.
echo ================================================================
echo.

REM Start Stable Diffusion in new window with venv_sd
echo [1/2] Dang khoi dong Stable Diffusion API (venv_sd - PyTorch 2.0.1)...
start "Stable Diffusion API" cmd /k "cd /d i:\AI-Assistant\stable-diffusion-webui && call venv_sd\Scripts\activate.bat && python webui.py --api --xformers --no-half-vae --disable-safe-unpickle --skip-prepare-environment --skip-version-check"

echo Doi 15 giay de Stable Diffusion khoi dong hoan tat...
timeout /t 15 /nobreak > nul

REM Start ChatBot in new window with venv_chatbot
echo [2/2] Dang khoi dong ChatBot (venv_chatbot - PyTorch 2.4.0 + Local Models)...
start "ChatBot WebUI" cmd /k "cd /d i:\AI-Assistant\ChatBot && call venv_chatbot\Scripts\activate.bat && python app.py"

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
