@echo off
REM ================================================================================
REM  VistralS2T - CLI Diarization Runner
REM  Run diarization pipeline without Web UI for better performance
REM ================================================================================

echo.
echo ================================================================================
echo  VistralS2T - Diarization CLI
echo ================================================================================
echo.

if "%~1"=="" (
    echo Error: Please provide audio file path
    echo Usage: run_diarization_cli.bat "path\to\audio.mp3"
    echo.
    pause
    exit /b 1
)

set AUDIO_FILE=%~1

if not exist "%AUDIO_FILE%" (
    echo Error: Audio file not found: %AUDIO_FILE%
    pause
    exit /b 1
)

echo Audio file: %AUDIO_FILE%
echo.

REM Activate virtual environment
call app\s2t\Scripts\activate.bat

REM Set environment variable for audio path
set AUDIO_PATH=%AUDIO_FILE%

REM Run the diarization script
cd app\core
python run_with_diarization.py

pause
