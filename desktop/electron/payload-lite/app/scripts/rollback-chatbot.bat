@echo off
REM ============================================================
REM Chatbot Service Rollback Script for Windows
REM ============================================================

setlocal enabledelayedexpansion

echo.
echo ========================================
echo   Chatbot Service Rollback
echo ========================================
echo.

set SERVICE_DIR=%~dp0..\services\chatbot
set BACKUP_DIR=%~dp0..\backups

REM List available backups
echo Available backups:
echo ----------------------------------------
set count=0
for /f "delims=" %%f in ('dir /b /o-d "%BACKUP_DIR%\chatbot_backup_*.zip" 2^>nul') do (
    set /a count+=1
    echo !count!. %%f
    set "backup!count!=%%f"
)

if %count%==0 (
    echo [ERROR] No backups found in %BACKUP_DIR%
    exit /b 1
)

echo.
set /p choice="Enter backup number to restore (or 'q' to quit): "

if /i "%choice%"=="q" (
    echo Cancelled.
    exit /b 0
)

set "selected=!backup%choice%!"
if not defined selected (
    echo [ERROR] Invalid selection
    exit /b 1
)

echo.
echo Selected: %selected%
echo.
set /p confirm="Are you sure you want to rollback? (y/n): "

if /i not "%confirm%"=="y" (
    echo Cancelled.
    exit /b 0
)

echo.
echo [1/3] Stopping services...
echo ----------------------------------------

REM Stop Flask if running (find and kill python processes on port 5001)
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :5001 ^| findstr LISTENING 2^>nul') do (
    echo Stopping process %%a on port 5001...
    taskkill /PID %%a /F 2>nul
)
echo [OK] Services stopped

echo.
echo [2/3] Restoring backup...
echo ----------------------------------------

set BACKUP_FILE=%BACKUP_DIR%\%selected%

REM Create restore directory
if exist "%SERVICE_DIR%\Storage.bak" rmdir /s /q "%SERVICE_DIR%\Storage.bak"
if exist "%SERVICE_DIR%\Storage" (
    rename "%SERVICE_DIR%\Storage" "Storage.bak"
)

REM Extract backup
powershell -Command "Expand-Archive -Path '%BACKUP_FILE%' -DestinationPath '%SERVICE_DIR%\Storage' -Force"

if exist "%SERVICE_DIR%\Storage" (
    echo [OK] Backup restored
    if exist "%SERVICE_DIR%\Storage.bak" rmdir /s /q "%SERVICE_DIR%\Storage.bak"
) else (
    echo [ERROR] Restore failed, reverting...
    if exist "%SERVICE_DIR%\Storage.bak" rename "%SERVICE_DIR%\Storage.bak" "Storage"
    exit /b 1
)

echo.
echo [3/3] Verifying restoration...
echo ----------------------------------------

cd /d "%SERVICE_DIR%"
python -c "from database import ConversationRepository; print('[OK] Database modules loaded')" 2>nul
if errorlevel 1 (
    echo [WARN] Could not verify database modules
) else (
    echo [OK] System verified
)

echo.
echo ========================================
echo   Rollback Complete!
echo ========================================
echo.
echo Restored from: %selected%
echo.
echo To restart the service:
echo   cd %SERVICE_DIR%
echo   python app.py
echo.

endlocal
