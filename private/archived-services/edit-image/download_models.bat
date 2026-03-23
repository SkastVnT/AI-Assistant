@echo off
REM ============================================================================
REM Download Models for Edit Image Tool
REM ============================================================================
REM Local models = MUCH FASTER than HuggingFace API
REM ============================================================================

echo.
echo ============================================================
echo   Edit Image Tool - Model Downloader
echo ============================================================
echo.
echo Choose download option:
echo.
echo   1. Essential only (~22GB) - RECOMMENDED for quick start
echo   2. Essential + Anime (~35GB)
echo   3. All models (~65GB)
echo   4. List all available models
echo   5. Exit
echo.

set /p choice="Enter choice (1-5): "

if "%choice%"=="1" goto essential
if "%choice%"=="2" goto anime
if "%choice%"=="3" goto all
if "%choice%"=="4" goto list
if "%choice%"=="5" goto end

echo Invalid choice. Please try again.
pause
goto :eof

:essential
echo.
echo Downloading ESSENTIAL models (~22GB)...
echo This includes: SDXL, InstructPix2Pix, IP-Adapter, InstantID, SAM, Real-ESRGAN
echo.
python download_models.py --essential
goto done

:anime
echo.
echo Downloading ESSENTIAL + ANIME models (~35GB)...
echo.
python download_models.py --recommended
goto done

:all
echo.
echo Downloading ALL models (~65GB)...
echo.
python download_models.py --all
goto done

:list
echo.
python download_models.py --list
echo.
pause
goto :eof

:done
echo.
echo ============================================================
echo   Download Complete!
echo ============================================================
echo.
echo Next steps:
echo   1. Update config/settings.yaml with model paths (already configured)
echo   2. Run: start.bat
echo.
pause
goto :eof

:end
echo Bye!
