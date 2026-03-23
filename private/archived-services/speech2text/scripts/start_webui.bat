@echo off
REM ================================================================================
REM  VistralS2T - Web UI Launcher
REM  Quick launcher for the web interface
REM ================================================================================

echo.
echo ================================================================================
echo  Starting VistralS2T Web UI...
echo ================================================================================
echo.

REM Activate virtual environment
call app\s2t\Scripts\activate.bat

REM Run web UI from app directory without changing to it
python app\web_ui.py

pause
