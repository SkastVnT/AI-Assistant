@echo off
REM ============================================================================
REM Install Google Gemini Package for Speech2Text Services
REM ============================================================================

echo.
echo ============================================================================
echo Installing Google Gemini API Package
echo ============================================================================
echo.

REM Activate virtual environment if it exists
if exist "s2t\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment: s2t
    call s2t\Scripts\activate.bat
) else (
    echo [WARN] Virtual environment not found. Installing globally...
)

echo.
echo [STEP 1/2] Installing google-generativeai package...
pip install google-generativeai>=0.3.0

echo.
echo [STEP 2/2] Verifying installation...
python -c "import google.generativeai as genai; print('[OK] google-generativeai installed successfully')"

echo.
echo ============================================================================
echo Installation Complete!
echo ============================================================================
echo.
echo Next steps:
echo 1. Get your free Gemini API key at: https://aistudio.google.com/apikey
echo 2. Add to .env file: GEMINI_API_KEY=your_api_key_here
echo 3. Run the application: python app\web_ui.py
echo.

pause
