@echo off
REM ============================================================================
REM Quick WebUI Dependencies Installer v3.5
REM ============================================================================

echo.
echo ============================================================================
echo  Installing WebUI Dependencies
echo ============================================================================
echo.

REM Check if venv exists
if not exist "app\s2t\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found!
    echo Please run: .\rebuild_project.bat
    pause
    exit /b 1
)

REM Activate venv
call app\s2t\Scripts\activate.bat

echo Installing Flask packages...
pip install flask>=3.0.2
pip install flask-cors>=4.0.0
pip install flask-socketio>=5.3.6
pip install python-socketio>=5.11.0

echo.
echo Installing async mode packages...
pip install eventlet>=0.35.0
pip install greenlet>=3.0.0

echo.
echo ============================================================================
echo  Installation Complete!
echo ============================================================================
echo.
echo Now you can run: .\start_webui.bat
echo.
pause
