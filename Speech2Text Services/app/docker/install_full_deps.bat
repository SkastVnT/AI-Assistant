@echo off
REM ========================================
REM Install Full Dependencies in Container
REM ========================================

echo ========================================
echo  Installing Full Dependencies
echo ========================================

REM Check if container is running
docker ps | findstr "s2t-system" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Container 's2t-system' is not running!
    echo [ERROR] Please start container first: docker compose up -d
    pause
    exit /b 1
)

echo [INSTALL] Installing pyannote.audio and dependencies...
docker exec s2t-system pip3 install --no-cache-dir ^
    pyannote.audio==3.1.1 ^
    pyannote.core==5.0.0 ^
    pyannote.pipeline==3.0.1 ^
    pyannote.database==5.1.3 ^
    pyannote.metrics==3.2.1

echo.
echo [INSTALL] Installing additional ML packages...
docker exec s2t-system pip3 install --no-cache-dir ^
    pytorch-lightning==2.0.9.post0 ^
    lightning==2.0.9.post0 ^
    torchmetrics

echo.
echo [INSTALL] Installing API clients...
docker exec s2t-system pip3 install --no-cache-dir ^
    openai ^
    google-generativeai

echo.
echo [SUCCESS] Full dependencies installed!
echo [INFO] Container is ready for advanced features
echo.

pause
