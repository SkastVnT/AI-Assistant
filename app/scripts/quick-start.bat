@echo off
REM =============================================================================
REM AI-Assistant - Quick Start Script
REM =============================================================================
REM Starts all core services using Docker Compose
REM =============================================================================

echo.
echo  ========================================
echo   AI-Assistant Quick Start
echo  ========================================
echo.

REM Check if Docker is installed
where docker >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Docker is not installed or not in PATH
    echo Please install Docker Desktop from https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)

REM Check if Docker is running
docker info >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] Docker is not running
    echo Please start Docker Desktop and try again
    pause
    exit /b 1
)

echo [OK] Docker is installed and running
echo.

REM Check if .env exists
if not exist .env (
    echo [INFO] Creating .env from .env.example...
    copy .env.example .env >nul 2>nul
    if %ERRORLEVEL% neq 0 (
        echo [WARN] Could not create .env file
        echo Please copy .env.example to .env and configure it
    ) else (
        echo [OK] .env file created
        echo [WARN] Please edit .env and add your API keys before continuing
        echo.
        pause
    )
)

echo [1] Starting core services (MongoDB, Redis, Hub, Chatbot)...
echo.

docker-compose up -d mongodb redis hub-gateway chatbot text2sql document-intelligence

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Failed to start services
    echo Check Docker logs for more information: docker-compose logs
    pause
    exit /b 1
)

echo.
echo ========================================
echo  Services Started Successfully!
echo ========================================
echo.
echo  MongoDB:              http://localhost:27017
echo  Redis:                localhost:6379
echo  Hub Gateway:          http://localhost:3000
echo  Chatbot:              http://localhost:5000
echo  Text2SQL:             http://localhost:5002
echo  Document Intelligence: http://localhost:5003
echo.
echo  To view logs: docker-compose logs -f
echo  To stop all:  docker-compose down
echo.
echo ========================================

REM Open browser to chatbot
echo Opening Chatbot in browser...
start http://localhost:5000

pause
