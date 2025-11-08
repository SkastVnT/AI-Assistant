@echo off
echo ================================================================
echo   SETUP DOCUMENT INTELLIGENCE VIRTUAL ENVIRONMENT
echo ================================================================
echo.
echo Tao virtual environment rieng cho Document Intelligence Service...
echo Moi truong nay su dung PaddleOCR + Gemini 2.0 Flash
echo.

cd /d "i:\AI-Assistant\Document Intelligence Service"

REM Create venv
echo [1/4] Dang tao virtual environment venv_dis...
python -m venv venv_dis
echo [OK] Da tao venv_dis
echo.

REM Activate venv
echo [2/4] Dang kich hoat venv_dis...
call venv_dis\Scripts\activate.bat
echo [OK] Da kich hoat venv_dis
echo.

REM Upgrade pip
echo [3/4] Dang nang cap pip...
python -m pip install --upgrade pip
echo [OK] Da nang cap pip
echo.

REM Install requirements
echo [4/4] Dang cai cac dependencies cua Document Intelligence...
pip install -r requirements.txt
echo [OK] Da cai tat ca dependencies
echo.

REM Verify installation
echo ================================================================
echo   KIEM TRA CAI DAT
echo ================================================================
python -c "import paddleocr; import google.generativeai as genai; print('PaddleOCR: OK'); print('Gemini API: OK')"
echo.

echo ================================================================
echo   HOAN THANH!
echo ================================================================
echo.
echo Virtual environment da duoc tao tai: venv_dis
echo.
echo De khoi dong Document Intelligence Service:
echo   cd "i:\AI-Assistant\Document Intelligence Service"
echo   venv_dis\Scripts\activate.bat
echo   python app.py
echo.
echo Hoac su dung: start_service.bat
echo.
echo FEATURES:
echo   - PaddleOCR (Vietnamese OCR)
echo   - Gemini 2.0 Flash AI Enhancement
echo   - PDF + Image Processing
echo.
pause
