@echo off
echo ================================================================
echo   AI ASSISTANT HUB - MAIN GATEWAY
echo ================================================================
echo.
echo Khoi dong Hub Gateway tren port 3000...
echo.
echo Tu day ban co the truy cap tat ca cac services:
echo   - ChatBot (5000)
echo   - Text2SQL (5001)
echo   - Speech2Text (5002)
echo   - Document Intelligence (5003)
echo   - RAG Services (5004)
echo   - Stable Diffusion (7860)
echo.

cd /d i:\AI-Assistant

REM Check if virtual environment exists
if not exist venv_hub (
    echo [INFO] Chua co virtual environment cho Hub
    echo [INFO] Dang tao venv_hub...
    python -m venv venv_hub
    call venv_hub\Scripts\activate.bat
    echo [INFO] Dang cai dependencies...
    pip install flask flask-cors python-dotenv
) else (
    call venv_hub\Scripts\activate.bat
)

echo.
echo [OK] Virtual environment da duoc kich hoat
echo.
echo ================================================================
echo   STARTING HUB ON PORT 3000
echo ================================================================
echo.

python src\hub.py

pause
