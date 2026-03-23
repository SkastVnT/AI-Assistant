@echo off
echo ================================================================================
echo VISTRAL-7B SPEECH TO TEXT - ULTRA FAST MODE
echo ================================================================================
echo.

REM Activate virtual environment
call s2t\Scripts\activate.bat

REM Run Vistral script
python core\run_dual_vistral.py

REM Pause to see results
pause
