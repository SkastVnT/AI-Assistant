@echo off
echo ================================================================
echo   SETUP ALL VIRTUAL ENVIRONMENTS - AI ASSISTANT
echo ================================================================
echo.
echo Script nay se tao 2 virtual environments:
echo   1. venv_sd - Stable Diffusion (PyTorch 2.0.1)
echo   2. venv_chatbot - ChatBot + Local Models (PyTorch 2.4.0)
echo.
echo Thoi gian du kien: 10-20 phut (tuy toc do mang)
echo.
pause

REM Setup Stable Diffusion venv
echo.
echo ================================================================
echo   BUOC 1: SETUP STABLE DIFFUSION VENV
echo ================================================================
cd /d i:\AI-Assistant\stable-diffusion-webui
call setup_venv_sd.bat

echo.
echo Nhan phim bat ky de tiep tuc voi ChatBot setup...
pause > nul

REM Setup ChatBot venv
echo.
echo ================================================================
echo   BUOC 2: SETUP CHATBOT VENV
echo ================================================================
cd /d i:\AI-Assistant\ChatBot
call setup_venv_chatbot.bat

echo.
echo ================================================================
echo   HOAN THANH TAT CA!
echo ================================================================
echo.
echo Da setup xong 2 virtual environments:
echo   [OK] i:\AI-Assistant\stable-diffusion-webui\venv_sd
echo   [OK] i:\AI-Assistant\ChatBot\venv_chatbot
echo.
echo De khoi dong ca 2 dich vu:
echo   cd i:\AI-Assistant\scripts\startup
echo   start_chatbot_with_sd.bat
echo.
echo Hoac khoi dong rieng le:
echo   - SD only: i:\AI-Assistant\stable-diffusion-webui\venv_sd\Scripts\activate.bat
echo   - ChatBot only: i:\AI-Assistant\ChatBot\venv_chatbot\Scripts\activate.bat
echo.
pause
