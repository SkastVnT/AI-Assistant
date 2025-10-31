@echo off
REM Quick fix for WebUI eventlet issue

echo.
echo Fixing WebUI dependencies...
echo.

call app\s2t\Scripts\activate.bat

echo Installing eventlet...
pip install eventlet==0.35.0 -q

echo Installing greenlet...
pip install greenlet>=3.0.0 -q

echo.
echo Done! Now try: .\start_webui.bat
echo.
pause
