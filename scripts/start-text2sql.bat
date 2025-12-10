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

cd services\text2sql

REM Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    echo Using virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Using global Python...
)

echo.
echo Starting Text2SQL Service...
echo Access at: http://localhost:5002
echo.
python app_simple.py

pause
