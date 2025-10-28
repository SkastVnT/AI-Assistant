@echo off
echo ============================================
echo   AI ASSISTANT - FULL STACK
echo   ChatBot + Stable Diffusion
echo ============================================
echo.

echo [1/2] Khoi dong Stable Diffusion WebUI...
start "Stable Diffusion API" cmd /k "cd i:\AI-Assistant && start_stable_diffusion_api.bat"

echo Cho 10 giay de Stable Diffusion khoi dong...
timeout /t 10 /nobreak

echo.
echo [2/2] Khoi dong ChatBot...
start "ChatBot" cmd /k "cd i:\AI-Assistant\ChatBot && python app.py"

echo.
echo ============================================
echo   TAT CA DICH VU DA KHOI DONG!
echo ============================================
echo.
echo Stable Diffusion WebUI: http://127.0.0.1:7860
echo ChatBot Interface: http://127.0.0.1:5000
echo.
echo Mo trinh duyet va truy cap http://127.0.0.1:5000
echo ============================================
echo.
echo Nhan phim bat ky de dong cua so nay...
pause
