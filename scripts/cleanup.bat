@echo off
REM =============================================================================
REM AI-Assistant - Cleanup Script
REM =============================================================================
REM This script helps identify and optionally remove unused files
REM Run with /preview to see what would be deleted without actually deleting
REM =============================================================================

setlocal enabledelayedexpansion

echo.
echo  ========================================
echo   AI-Assistant Cleanup Tool
echo  ========================================
echo.

set PREVIEW_MODE=0
if "%1"=="/preview" set PREVIEW_MODE=1
if "%1"=="--preview" set PREVIEW_MODE=1
if "%1"=="-p" set PREVIEW_MODE=1

if %PREVIEW_MODE%==1 (
    echo [MODE] Preview only - no files will be deleted
) else (
    echo [MODE] Delete mode - files will be moved to _trash folder
)
echo.

REM Create trash folder for safe deletion
if not exist "_trash" mkdir "_trash"
if not exist "_trash\archives" mkdir "_trash\archives"
if not exist "_trash\deprecated" mkdir "_trash\deprecated"

echo ========================================
echo  Files identified for cleanup:
echo ========================================
echo.

set COUNT=0

echo [1] Old archive summaries (docs/archives/old-summaries/)
echo     - 24 old summary files from previous versions
if %PREVIEW_MODE%==0 (
    if exist "docs\archives\old-summaries" (
        move "docs\archives\old-summaries" "_trash\archives\" >nul 2>nul
        echo     [MOVED] -> _trash/archives/old-summaries
    )
) else (
    echo     [PREVIEW] Would move to _trash/archives/old-summaries
)
set /a COUNT+=24
echo.

echo [2] Deprecated scripts (scripts/deprecated/)
echo     - 8 old test and setup scripts
if %PREVIEW_MODE%==0 (
    if exist "scripts\deprecated" (
        move "scripts\deprecated" "_trash\deprecated\" >nul 2>nul
        echo     [MOVED] -> _trash/deprecated/deprecated
    )
) else (
    echo     [PREVIEW] Would move to _trash/deprecated/deprecated
)
set /a COUNT+=8
echo.

echo [3] Archive scripts (scripts/archive/)
echo     - 21 old batch scripts
if %PREVIEW_MODE%==0 (
    if exist "scripts\archive" (
        move "scripts\archive" "_trash\deprecated\" >nul 2>nul
        echo     [MOVED] -> _trash/deprecated/archive
    )
) else (
    echo     [PREVIEW] Would move to _trash/deprecated/archive
)
set /a COUNT+=21
echo.

echo [4] Python cache files
for /r %%d in (__pycache__) do (
    if exist "%%d" (
        if %PREVIEW_MODE%==0 (
            rd /s /q "%%d" >nul 2>nul
        )
        set /a COUNT+=1
    )
)
echo     [CLEANED] __pycache__ directories
echo.

echo [5] Temporary files
for /r %%f in (*.pyc *.pyo .DS_Store Thumbs.db) do (
    if exist "%%f" (
        if %PREVIEW_MODE%==0 (
            del /q "%%f" >nul 2>nul
        )
        set /a COUNT+=1
    )
)
echo     [CLEANED] .pyc, .pyo, .DS_Store, Thumbs.db files
echo.

echo ========================================
echo  Summary
echo ========================================
echo.
echo  Items processed: ~%COUNT%
echo.

if %PREVIEW_MODE%==1 (
    echo  This was a PREVIEW. To actually clean up, run:
    echo    cleanup.bat
    echo.
    echo  Or to delete permanently without backup:
    echo    cleanup.bat /force
) else (
    echo  Files have been moved to _trash folder.
    echo  You can review and permanently delete them:
    echo    rd /s /q _trash
    echo.
    echo  Or restore them if needed.
)

echo.
echo ========================================

pause
