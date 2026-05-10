@echo off
REM ==================================================
REM AI-Assistant - Start MCP Server
REM Shortcut from root directory
REM ==================================================

REM Force UTF-8 encoding to prevent Unicode errors
chcp 65001 >nul 2>&1

REM Navigate to project root (parent of scripts folder)
cd /d "%~dp0.."

echo.
echo ============================================
echo   AI-Assistant MCP Server Launcher
echo ============================================
echo.

REM Get the root directory (parent of scripts folder)
cd /d "%~dp0.."

REM Check if MCP Server exists
if not exist "services\mcp-server\server.py" (
    echo [ERROR] MCP Server not found!
    echo Please ensure services/mcp-server/server.py exists
    pause
    exit /b 1
)

REM Navigate to MCP Server directory
cd services\mcp-server

REM Call the actual start script
call start-mcp-server.bat
