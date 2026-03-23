@echo off
chcp 65001 > nul
title Setup - Speech-to-Text System

echo ================================================================================
echo SETUP AFTER CLONE - SPEECH-TO-TEXT SYSTEM
echo ================================================================================
echo.

echo [1/4] Creating virtual environment...
python -m venv app\s2t
if errorlevel 1 (
    echo ERROR: Failed to create virtual environment
    pause
    exit /b 1
)
echo OK!
echo.

echo [2/4] Installing dependencies...
call app\s2t\Scripts\activate.bat
pip install --upgrade pip
pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo OK!
echo.

echo [3/4] Creating output folders...
if not exist app\output\raw mkdir app\output\raw
if not exist app\output\vistral mkdir app\output\vistral
if not exist app\output\dual mkdir app\output\dual
if not exist app\audio mkdir app\audio
if not exist app\logs mkdir app\logs
echo OK!
echo.

echo [4/4] Checking configuration...
if not exist app\config\.env (
    echo.
    echo IMPORTANT: Create app\config\.env file with:
    echo   HF_API_TOKEN=your_token_here
    echo   AUDIO_PATH=C:\path\to\audio.mp3
    echo.
    echo Get token at: https://huggingface.co/settings/tokens
    echo.
)
echo.

echo ================================================================================
echo SETUP COMPLETE!
echo ================================================================================
echo.
echo Next steps:
echo   1. Set HF_API_TOKEN in app\config\.env
echo   2. Put audio file path in app\config\.env
echo   3. Run: run.bat
echo.
echo To check installation: python check.py
echo.
pause
