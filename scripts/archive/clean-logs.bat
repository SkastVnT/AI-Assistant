@echo off
title AI Assistant - Clean Logs
color 0C

echo ================================================================================
echo.
echo                     Clean All Service Logs
echo.
echo ================================================================================
echo.
echo This will delete all log files from all services.
echo.
echo Logs to be cleaned:
echo   - resources/logs/
echo   - services/*/logs/
echo   - services/*/output/
echo   - services/*/temp/
echo.
echo WARNING: This action cannot be undone!
echo.
pause

echo.
echo Cleaning logs...
echo.

REM Clean main logs directory
if exist "resources\logs\" (
    echo Cleaning resources\logs\...
    del /q /s "resources\logs\*.*" 2>nul
    for /d %%p in ("resources\logs\*") do rmdir "%%p" /s /q 2>nul
    echo ✓ Cleaned resources\logs\
) else (
    echo ✗ resources\logs\ not found
)

REM Clean service-specific logs
echo.
echo Cleaning service logs...
echo.

for /d %%s in (services\*) do (
    if exist "%%s\logs\" (
        echo Cleaning %%s\logs\...
        del /q /s "%%s\logs\*.*" 2>nul
        for /d %%p in ("%%s\logs\*") do rmdir "%%p" /s /q 2>nul
        echo ✓ Cleaned %%s\logs\
    )
    
    if exist "%%s\output\" (
        echo Cleaning %%s\output\...
        del /q /s "%%s\output\*.*" 2>nul
        for /d %%p in ("%%s\output\*") do rmdir "%%p" /s /q 2>nul
        echo ✓ Cleaned %%s\output\
    )
    
    if exist "%%s\temp\" (
        echo Cleaning %%s\temp\...
        del /q /s "%%s\temp\*.*" 2>nul
        for /d %%p in ("%%s\temp\*") do rmdir "%%p" /s /q 2>nul
        echo ✓ Cleaned %%s\temp\
    )
)

REM Clean Python cache
echo.
echo Cleaning Python cache...
for /r . %%d in (__pycache__) do (
    if exist "%%d" (
        rmdir "%%d" /s /q 2>nul
    )
)
for /r . %%f in (*.pyc *.pyo) do (
    if exist "%%f" del "%%f" /q 2>nul
)
echo ✓ Cleaned Python cache

REM Clean pytest cache
echo.
echo Cleaning pytest cache...
if exist ".pytest_cache\" (
    rmdir ".pytest_cache" /s /q 2>nul
    echo ✓ Cleaned .pytest_cache
)

echo.
echo ================================================================================
echo   ✅ All logs cleaned successfully!
echo ================================================================================
echo.
pause
