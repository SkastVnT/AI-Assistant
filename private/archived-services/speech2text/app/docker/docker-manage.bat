@echo off
REM ============================================
REM Docker Build and Run Script for Windows
REM ============================================

echo ========================================
echo  Starting Speech2Text Docker Container
echo ========================================
echo.

cd /d "%~dp0"

REM Check if Docker is running
docker ps >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running!
    echo Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo [OK] Docker is running
echo.

REM Create required directories
if not exist "input" mkdir input
if not exist "output" mkdir output
if not exist "logs" mkdir logs

echo [OK] Directories created
echo.

REM Check if .env exists
if not exist ".env" (
    echo [WARNING] .env file not found!
    echo Creating .env from config/.env...
    copy /Y "..\config\.env" ".env" >nul
)

echo ========================================
echo  Choose an option:
echo ========================================
echo  1. Build Docker image (fast - essential deps only)
echo  2. Start containers (docker compose up -d)
echo  3. Build and start (build + up)
echo  4. Install full dependencies (pyannote, etc.)
echo  5. Stop containers (docker compose down)
echo  6. View logs (docker compose logs -f)
echo  7. Check status (docker ps)
echo ========================================
echo.

set /p choice="Enter your choice (1-7): "

if "%choice%"=="1" goto build
if "%choice%"=="2" goto start
if "%choice%"=="3" goto build_and_start
if "%choice%"=="4" goto install_deps
if "%choice%"=="5" goto stop
if "%choice%"=="6" goto logs
if "%choice%"=="7" goto status

echo Invalid choice!
pause
exit /b 1

:build
echo.
echo [BUILD] Building Docker image...
docker compose -f docker-compose.windows.yml build
if errorlevel 1 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)
echo [OK] Build complete!
pause
exit /b 0

:start
echo.
echo [START] Starting containers...
docker compose -f docker-compose.windows.yml up -d
if errorlevel 1 (
    echo [ERROR] Failed to start containers!
    pause
    exit /b 1
)
echo [OK] Containers started!
echo.
echo View logs with: docker compose -f docker-compose.windows.yml logs -f
pause
exit /b 0

:build_and_start
echo.
echo [BUILD] Building Docker image...
docker compose -f docker-compose.windows.yml build
if errorlevel 1 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)
echo [OK] Build complete!
echo.
echo [START] Starting containers...
docker compose -f docker-compose.windows.yml up -d
if errorlevel 1 (
    echo [ERROR] Failed to start containers!
    pause
    exit /b 1
)
echo [OK] Containers started!
echo.
echo View logs with: docker compose -f docker-compose.windows.yml logs -f
pause
exit /b 0

:install_deps
echo.
echo [INSTALL] Installing full dependencies in container...
echo [INFO] This will install pyannote.audio and other heavy packages
echo [INFO] This may take 5-10 minutes...
echo.
call install_full_deps.bat
pause
exit /b 0

:stop
echo.
echo [STOP] Stopping containers...
docker compose -f docker-compose.windows.yml down
echo [OK] Containers stopped!
pause
exit /b 0

:logs
echo.
echo [LOGS] Showing container logs (Ctrl+C to exit)...
docker compose -f docker-compose.windows.yml logs -f
pause
exit /b 0

:status
echo.
echo [STATUS] Container status:
docker ps -a --filter "name=s2t"
echo.
echo [IMAGES] Images:
docker images --filter "reference=vistral-s2t"
pause
exit /b 0
