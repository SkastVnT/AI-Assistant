@echo off
echo ========================================
echo   Starting MCP Server V2.0 (WITH MEMORY)
echo ========================================
echo.
echo Service: Model Context Protocol Server V2.0
echo Type: AI Assistant Protocol + Memory System
echo Path: services/mcp-server/
echo.
echo Features:
echo   - File Search ^& Management
echo   - Project Information
echo   - Log Analysis
echo   - Code Assistant
echo   - Resources ^& Prompts
echo   ** MEMORY SYSTEM - Persistent across sessions **
echo   ** AI-Powered Observations **
echo   ** Search History **
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
    echo [WARN] MCP SDK not found in environment
    echo [INFO] Installing MCP SDK...
    pip install "mcp[cli]>=1.0.0"
    if errorlevel 1 (
        echo [ERROR] Failed to install MCP SDK!
        pause
        exit /b 1
    )
    echo [OK] MCP SDK installed successfully
)

REM Create memory directory if not exists
if not exist "..\..\resources\memory" mkdir "..\..\resources\memory"

echo.
echo ============================================
echo Starting MCP Server V2.0 WITH MEMORY...
echo ============================================
echo.
echo Available Clients:
echo   - Claude Desktop (Recommended)
echo   - VS Code with MCP Extension
echo   - Custom MCP Clients
echo.
echo Memory Features:
echo   - Persistent storage in SQLite
echo   - Search across all sessions
echo   - AI-generated observations
echo   - Full-text search
echo.
echo Press Ctrl+C to stop server
echo.

REM Start the V2 server
python server_v2_memory.py

if errorlevel 1 (
    echo.
    echo [ERROR] Server stopped with error!
    pause
    exit /b 1
)

echo.
echo [INFO] Server stopped.
echo [INFO] All session data has been saved to memory.
pause
