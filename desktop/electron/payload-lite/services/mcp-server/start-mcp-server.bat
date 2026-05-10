@echo off
echo ========================================
echo   Starting MCP Server
echo ========================================
echo.
echo Service: Model Context Protocol Server
echo Type: AI Assistant Protocol
echo Path: services/mcp-server/
echo.
echo Features:
echo   - File Search ^& Management
echo   - Project Information
echo   - Log Analysis
echo   - Code Assistant
echo   - Resources ^& Prompts
echo.

REM Get project root (2 levels up from services/mcp-server)
set "PROJECT_ROOT=%~dp0..\.."
cd /d "%PROJECT_ROOT%"

REM Setup virtual environment and dependencies
call scripts\setup-venv.bat
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to setup environment
    pause
    exit /b 1
)

REM Navigate to MCP server directory
cd services\mcp-server

REM Check if MCP package is installed
echo.
echo Checking MCP SDK...
python -c "import mcp" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [ERROR] MCP SDK is not installed!
    echo [INFO] Please run the following command manually:
    echo.
    echo     pip install "mcp[cli]>=1.0.0"
    echo.
    pause
    exit /b 1
)

echo.
echo Starting MCP Server...
echo.
echo Available Clients:
echo   - Claude Desktop (Recommended)
echo   - VS Code with MCP Extension
echo   - Custom MCP Clients
echo.
echo Press Ctrl+C to stop server
echo.

REM Start the server
python server.py

if errorlevel 1 (
    echo.
    echo [ERROR] Server stopped with error!
    pause
    exit /b 1
)

echo.
echo [INFO] Server stopped.
pause
