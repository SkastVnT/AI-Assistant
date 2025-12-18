@echo off
REM Navigate to project root (parent of scripts folder)
cd /d "%~dp0.."

echo ========================================
echo   Starting Document Intelligence Service
echo ========================================
echo.
echo Service: OCR + AI Document Analysis
echo Port: 5003
echo Path: services/document-intelligence/
echo.
echo Features:
echo   - PaddleOCR (Vietnamese support)
echo   - Gemini AI Analysis
echo   - Table Detection
echo   - Multi-format Support
echo.

REM Setup virtual environment and dependencies
call "%~dp0setup-venv.bat"
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to setup environment
    pause
    exit /b 1
)

cd services\document-intelligence

echo.
echo Starting Document Intelligence Service...
echo Access at: http://localhost:5003
echo.
..\..\\.venv\Scripts\python.exe app.py

pause
