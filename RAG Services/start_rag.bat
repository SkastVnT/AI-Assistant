@echo off
REM RAG Services Startup Script
REM Phase 1: Core RAG with FREE models

echo ========================================
echo   RAG Services - Startup
echo   100%% FREE - No API costs
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\" (
    echo [1/4] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ERROR: Failed to create virtual environment
        pause
        exit /b 1
    )
    echo   ✓ Virtual environment created
) else (
    echo [1/4] Virtual environment found
)

echo.
echo [2/4] Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo [3/4] Installing dependencies (first run may take a while)...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo   ✓ Dependencies installed

echo.
echo [4/4] Starting RAG Services...
echo.
echo ========================================
echo   Server will start at:
echo   http://localhost:5003
echo.
echo   FREE Models Used:
echo   - Embedding: vietnamese-sbert
echo   - VectorDB: ChromaDB (local)
echo.
echo   Phase 1: Core RAG ✓
echo   Next: Web UI coming soon!
echo ========================================
echo.

python app.py

pause
