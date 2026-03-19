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

start "core-hub-gateway" cmd /k "cd /d services\hub-gateway && ..\..\venv-core\Scripts\python.exe hub.py"
start "core-chatbot" cmd /k "cd /d services\chatbot && ..\..\venv-core\Scripts\python.exe run.py"
start "core-speech2text" cmd /k "cd /d services\speech2text\app && ..\..\..\venv-core\Scripts\python.exe web_ui.py"
start "core-text2sql" cmd /k "cd /d services\text2sql && ..\..\venv-core\Scripts\python.exe app.py"
start "core-document-intelligence" cmd /k "cd /d services\document-intelligence && ..\..\venv-core\Scripts\python.exe run.py"
start "core-mcp-server" cmd /k "cd /d services\mcp-server && ..\..\venv-core\Scripts\python.exe server.py"

echo [OK] Core services launched in separate terminals.
echo Hub: http://127.0.0.1:3000
echo ChatBot: http://127.0.0.1:5000
echo Speech2Text: http://127.0.0.1:5001
echo Text2SQL: http://127.0.0.1:5002
echo Document Intelligence: http://127.0.0.1:5003
