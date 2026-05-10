@echo off
REM =============================================================================
REM Expose Services to Public via Cloudflared (Windows)
REM =============================================================================

chcp 65001 >nul 2>&1
title AI-Assistant - Expose to Public

cd /d "%~dp0\.."

echo.
echo ================================================================================
echo                    EXPOSING SERVICES TO PUBLIC
echo                      via Cloudflared Tunnels
echo ================================================================================
echo.

REM Check if cloudflared is available
where cloudflared >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] cloudflared not found in PATH
    echo.
    echo Please download cloudflared from:
    echo https://github.com/cloudflare/cloudflared/releases/latest
    echo.
    echo After downloading, add it to your PATH or place it in this directory.
    echo.
    pause
    exit /b 1
)

echo [OK] cloudflared found
echo.

REM Kill existing tunnels
echo Stopping existing tunnels...
taskkill /F /IM cloudflared.exe >nul 2>&1
timeout /t 2 >nul

REM Check which services are running
echo.
echo Checking running services...
echo.

set HUB_RUNNING=0
set CHATBOT_RUNNING=0

netstat -ano | findstr ":3000" >nul 2>&1
if %ERRORLEVEL% EQU 0 set HUB_RUNNING=1

netstat -ano | findstr ":5000" >nul 2>&1
if %ERRORLEVEL% EQU 0 set CHATBOT_RUNNING=1

if %HUB_RUNNING% EQU 1 (
    echo [OK] Hub Gateway is running on port 3000
) else (
    echo [WARN] Hub Gateway is NOT running. Please start it first.
)

if %CHATBOT_RUNNING% EQU 1 (
    echo [OK] ChatBot is running on port 5000
) else (
    echo [WARN] ChatBot is NOT running. Please start it first.
)

echo.

REM Create tunnels
echo Creating tunnels...
echo.

if %HUB_RUNNING% EQU 1 (
    echo Starting tunnel for Hub Gateway ^(port 3000^)...
    start /B cloudflared tunnel --url http://localhost:3000 > logs\cloudflared_hub.log 2>&1
    timeout /t 5 >nul
)

if %CHATBOT_RUNNING% EQU 1 (
    echo Starting tunnel for ChatBot ^(port 5000^)...
    start /B cloudflared tunnel --url http://localhost:5000 > logs\cloudflared_chatbot.log 2>&1
    timeout /t 5 >nul
)

echo.
echo ================================================================================
echo                         PUBLIC URLS
echo ================================================================================
echo.
echo Check the following log files for your public URLs:
echo.
echo   Hub Gateway: logs\cloudflared_hub.log
echo   ChatBot:     logs\cloudflared_chatbot.log
echo.
echo Look for lines containing "trycloudflare.com"
echo.
echo ================================================================================
echo.
echo Press any key to view Hub Gateway tunnel log...
pause >nul

if exist logs\cloudflared_hub.log (
    type logs\cloudflared_hub.log | findstr "trycloudflare.com"
)

echo.
echo.
echo To stop tunnels: taskkill /F /IM cloudflared.exe
echo.
pause
