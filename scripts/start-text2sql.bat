@echo off
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
python app_simple.py

pause
