@echo off
REM ========================================
REM Test Docker Container Functionality
REM ========================================

echo ========================================
echo  Testing Docker Container
echo ========================================

REM Check if container is running
docker ps | findstr "s2t-system" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Container 's2t-system' is not running!
    echo [ERROR] Start container first: docker compose up -d
    pause
    exit /b 1
)

echo.
echo [TEST 1/5] Checking Python version...
docker exec s2t-system python3 --version
if errorlevel 1 (
    echo [FAIL] Python not found!
    exit /b 1
)
echo [OK] Python installed

echo.
echo [TEST 2/5] Checking PyTorch...
docker exec s2t-system python3 -c "import torch; print(f'PyTorch {torch.__version__}')"
if errorlevel 1 (
    echo [FAIL] PyTorch not installed!
    exit /b 1
)
echo [OK] PyTorch installed

echo.
echo [TEST 3/5] Checking Flask...
docker exec s2t-system python3 -c "import flask; print(f'Flask {flask.__version__}')"
if errorlevel 1 (
    echo [FAIL] Flask not installed!
    exit /b 1
)
echo [OK] Flask installed

echo.
echo [TEST 4/5] Checking faster-whisper...
docker exec s2t-system python3 -c "import faster_whisper; print('faster-whisper OK')"
if errorlevel 1 (
    echo [FAIL] faster-whisper not installed!
    exit /b 1
)
echo [OK] faster-whisper installed

echo.
echo [TEST 5/5] Checking transformers...
docker exec s2t-system python3 -c "import transformers; print(f'transformers {transformers.__version__}')"
if errorlevel 1 (
    echo [FAIL] transformers not installed!
    exit /b 1
)
echo [OK] transformers installed

echo.
echo ========================================
echo  OPTIONAL: Full Dependencies Test
echo ========================================
echo.
echo Testing pyannote.audio (skip if not installed)...
docker exec s2t-system python3 -c "import pyannote.audio; print('pyannote.audio OK')" 2>nul
if errorlevel 1 (
    echo [INFO] pyannote.audio not installed
    echo [INFO] Install with: docker-manage.bat → Option 4
) else (
    echo [OK] pyannote.audio installed
)

echo.
echo ========================================
echo  All Basic Tests Passed! ✅
echo ========================================
echo.
echo Container is ready for:
echo  - Audio transcription (Whisper)
echo  - Text processing (transformers)
echo  - Web UI (Flask)
echo.
echo To install full dependencies:
echo  - Run docker-manage.bat
echo  - Choose option 4
echo.

pause
