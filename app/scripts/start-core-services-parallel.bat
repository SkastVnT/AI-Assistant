@echo off
chcp 65001 >nul 2>&1

cd /d "%~dp0.."

if not exist "venv-core\Scripts\python.exe" (
    echo [ERROR] venv-core not found. Please create/install core profile first.
    echo Run: pyenv exec python -m venv venv-core ^&^& venv-core\Scripts\python -m pip install -r requirements\profile_core_services.txt
    pause
    exit /b 1
)

echo ==================================================
echo   Start Core Services (Parallel)
echo   Environment: venv-core
echo ==================================================

start "core-chatbot" cmd /k "cd /d services\chatbot && ..\..\venv-core\Scripts\python.exe run.py"
start "core-mcp-server" cmd /k "cd /d services\mcp-server && ..\..\venv-core\Scripts\python.exe server.py"

echo [OK] Core services launched in separate terminals.
echo ChatBot: http://127.0.0.1:5000
