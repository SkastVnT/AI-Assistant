@echo off
echo ========================================
echo   AI ASSISTANT - CHATBOT ONLY
echo   (Khong khoi dong Stable Diffusion)
echo ========================================
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
echo Dang khoi dong ChatBot Service...
echo Sau khi khoi dong, mo trinh duyet: http://127.0.0.1:5000
echo.
echo LUU Y: Tinh nang tao anh se KHONG hoat dong 
echo (can khoi dong Stable Diffusion rieng neu muon dung)
echo.
echo Nhan Ctrl+C de dung service.
echo ========================================
echo.

cd ChatBot
python app.py
