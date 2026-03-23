@echo off
REM Start Development Server with Hot Reload
echo ========================================
echo   AI Upscaler - Dev Server (Hot Reload)
echo ========================================
echo.
echo Installing watchdog if needed...
pip install watchdog>=2.0.0
echo.
echo Starting server with auto-reload...
echo Edit web_ui.py and save to see changes!
echo Press Ctrl+C to stop
echo.

cd /d "%~dp0"
python -m upscale_tool.dev_server

pause
