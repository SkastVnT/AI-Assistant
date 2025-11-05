@echo off
REM Quick restart script for Document Intelligence Service
echo ========================================
echo Document Intelligence Service
echo Quick Restart Script
echo ========================================
echo.

cd /d "%~dp0"

REM Activate virtual environment
echo Activating virtual environment...
call .\DIS\Scripts\activate.bat

REM Set environment variable for protobuf
echo Setting environment variables...
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

REM Start service
echo.
echo ========================================
echo Starting service...
echo ========================================
echo.
python app.py

pause
