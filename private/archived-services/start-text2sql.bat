@echo off
REM Force UTF-8 encoding to prevent Unicode errors
chcp 65001 >nul 2>&1

REM Navigate to project root (parent of scripts folder)
cd /d "%~dp0.."

echo ========================================
echo   Starting Text2SQL Service
echo ========================================
echo.
echo Service: Natural Language to SQL
echo Port: 5002
echo Path: services/text2sql/
echo.
echo Features:
echo   - SQLCoder-7B-2 Model
echo   - Gemini AI Integration
echo   - Schema Upload Support
echo   - SQL Query Generation
echo.

REM Setup virtual environment and dependencies
call "%~dp0setup-venv.bat"
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to setup environment
    pause
    exit /b 1
)

cd services\text2sql

echo.
echo Starting Text2SQL Service...
echo Access at: http://localhost:5002
echo.
echo UI: Modern Dark Theme with Grok AI
echo.
python app.py

pause
