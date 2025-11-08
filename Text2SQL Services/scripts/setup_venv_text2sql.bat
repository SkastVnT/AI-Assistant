@echo off
echo ================================================================
echo   SETUP TEXT2SQL VIRTUAL ENVIRONMENT
echo ================================================================
echo.
echo Tao virtual environment rieng cho Text2SQL Service...
echo Moi truong nay su dung Gemini API + ClickHouse + MongoDB
echo.

cd /d "i:\AI-Assistant\Text2SQL Services"

REM Create venv
echo [1/4] Dang tao virtual environment venv_text2sql...
python -m venv venv_text2sql
echo [OK] Da tao venv_text2sql
echo.

REM Activate venv
echo [2/4] Dang kich hoat venv_text2sql...
call venv_text2sql\Scripts\activate.bat
echo [OK] Da kich hoat venv_text2sql
echo.

REM Upgrade pip
echo [3/4] Dang nang cap pip...
python -m pip install --upgrade pip
echo [OK] Da nang cap pip
echo.

REM Install requirements
echo [4/4] Dang cai cac dependencies cua Text2SQL...
pip install -r requirements.txt
echo [OK] Da cai tat ca dependencies
echo.

REM Verify installation
echo ================================================================
echo   KIEM TRA CAI DAT
echo ================================================================
python -c "import flask; import google.generativeai as genai; import clickhouse_connect; print('Flask: OK'); print('Gemini API: OK'); print('ClickHouse: OK')"
echo.

echo ================================================================
echo   HOAN THANH!
echo ================================================================
echo.
echo Virtual environment da duoc tao tai: venv_text2sql
echo.
echo De khoi dong Text2SQL Service:
echo   cd "i:\AI-Assistant\Text2SQL Services"
echo   venv_text2sql\Scripts\activate.bat
echo   python app.py
echo.
echo FEATURES:
echo   - Natural Language to SQL Conversion
echo   - ClickHouse + MongoDB Support
echo   - Gemini AI Integration
echo.
pause
