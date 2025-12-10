@echo off
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

cd services\document-intelligence

REM Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    echo Using virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Using global Python...
)

echo.
echo Starting Document Intelligence Service...
echo Access at: http://localhost:5003
echo.
python app.py

pause
