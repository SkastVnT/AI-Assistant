@echo off
chcp 65001 > nul
title Speech-to-Text System - Qwen2.5-1.5B Fusion

echo ================================================================================
echo SPEECH-TO-TEXT SYSTEM - DUAL MODEL FUSION
echo ================================================================================
echo.

REM Activate virtual environment
call app\s2t\Scripts\activate.bat

REM Run main script
python run.py

echo.
pause
