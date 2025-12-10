@echo off
REM ================================================================================
REM  VistralS2T - Speaker Diarization Launcher
REM  Quick launcher for command-line diarization
REM ================================================================================

echo.
echo ================================================================================
echo  Starting VistralS2T Speaker Diarization...
echo ================================================================================
echo.

REM Navigate to scripts and run
cd app\scripts
call run_diarization.bat

pause
