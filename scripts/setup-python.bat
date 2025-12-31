@echo off
REM =============================================================================
REM AI-Assistant - Python Environment Setup with pyenv
REM =============================================================================
REM This script sets up Python environments for all services using pyenv
REM Prerequisites: pyenv-win installed (https://github.com/pyenv-win/pyenv-win)
REM =============================================================================

echo.
echo  ========================================
echo   AI-Assistant Python Setup (pyenv)
echo  ========================================
echo.

REM Check if pyenv is installed
where pyenv >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [ERROR] pyenv is not installed or not in PATH
    echo.
    echo To install pyenv-win:
    echo   1. Open PowerShell as Administrator
    echo   2. Run: Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/pyenv-win/pyenv-win/master/pyenv-win/install-pyenv-win.ps1" -OutFile "./install-pyenv-win.ps1"; &"./install-pyenv-win.ps1"
    echo   3. Restart your terminal
    echo.
    pause
    exit /b 1
)

echo [OK] pyenv is installed
echo.

REM Install required Python versions
echo [1/4] Installing Python 3.11.9 (main version)...
pyenv install 3.11.9 --skip-existing

echo.
echo [2/4] Installing Python 3.10.11 (text2sql compatibility)...
pyenv install 3.10.11 --skip-existing

echo.
echo [3/4] Setting global Python version to 3.11.9...
pyenv global 3.11.9

echo.
echo [4/4] Verifying installation...
echo.
echo Global Python version:
pyenv version

echo.
echo ========================================
echo  Python Versions Installed
echo ========================================
echo.
echo  Main project:     3.11.9
echo  Text2SQL service: 3.10.11
echo.
echo  Pyenv will automatically use the correct
echo  Python version based on .python-version files
echo.
echo ========================================

echo.
echo [NEXT] Setting up virtual environments for each service...
echo.

REM Create virtual environments for main services
echo Creating virtual environment for chatbot...
cd services\chatbot
python -m venv venv
if exist venv\Scripts\pip.exe (
    echo Installing chatbot dependencies...
    venv\Scripts\pip install --upgrade pip
    venv\Scripts\pip install -r requirements.txt
    echo [OK] Chatbot environment ready
) else (
    echo [WARN] Failed to create chatbot venv
)
cd ..\..

echo.
echo Creating virtual environment for hub-gateway...
cd services\hub-gateway
python -m venv venv
if exist venv\Scripts\pip.exe (
    echo Installing hub-gateway dependencies...
    venv\Scripts\pip install --upgrade pip
    venv\Scripts\pip install -r requirements.txt
    echo [OK] Hub-gateway environment ready
) else (
    echo [WARN] Failed to create hub-gateway venv
)
cd ..\..

echo.
echo Creating virtual environment for text2sql (Python 3.10)...
cd services\text2sql
REM Use pyenv local to switch to 3.10
pyenv local 3.10.11
python -m venv venv
if exist venv\Scripts\pip.exe (
    echo Installing text2sql dependencies...
    venv\Scripts\pip install --upgrade pip
    venv\Scripts\pip install -r requirements.txt
    echo [OK] Text2sql environment ready
) else (
    echo [WARN] Failed to create text2sql venv
)
cd ..\..

echo.
echo Creating virtual environment for document-intelligence...
cd services\document-intelligence
pyenv local 3.11.9
python -m venv venv
if exist venv\Scripts\pip.exe (
    echo Installing document-intelligence dependencies...
    venv\Scripts\pip install --upgrade pip
    if exist requirements.txt (
        venv\Scripts\pip install -r requirements.txt
    )
    echo [OK] Document-intelligence environment ready
) else (
    echo [WARN] Failed to create document-intelligence venv
)
cd ..\..

echo.
echo ========================================
echo  Setup Complete!
echo ========================================
echo.
echo  Virtual environments created in:
echo    - services/chatbot/venv
echo    - services/hub-gateway/venv
echo    - services/text2sql/venv
echo    - services/document-intelligence/venv
echo.
echo  To activate an environment:
echo    cd services\chatbot
echo    venv\Scripts\activate
echo.
echo ========================================

pause
