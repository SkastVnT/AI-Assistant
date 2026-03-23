@echo off
REM Force UTF-8 encoding to prevent Unicode errors
chcp 65001 >nul 2>&1

title AI Assistant - Start All Services
color 0A

REM Navigate to project root (parent of scripts folder)
cd /d "%~dp0.."

echo ================================================================================
echo.
echo     █████╗ ██╗    ██████╗ ██╗   ██╗██╗██╗     ██████╗ ███████╗██████╗ 
echo    ██╔══██╗██║    ██╔══██╗██║   ██║██║██║     ██╔══██╗██╔════╝██╔══██╗
echo    ███████║██║    ██████╔╝██║   ██║██║██║     ██║  ██║█████╗  ██████╔╝
echo    ██╔══██║██║    ██╔══██╗██║   ██║██║██║     ██║  ██║██╔══╝  ██╔══██╗
echo    ██║  ██║██║    ██████╔╝╚██████╔╝██║███████╗██████╔╝███████╗██║  ██║
echo    ╚═╝  ╚═╝╚═╝    ╚═════╝  ╚═════╝ ╚═╝╚══════╝╚═════╝ ╚══════╝╚═╝  ╚═╝
echo.
echo                         Start All Services v3.0
echo ================================================================================
echo.
echo This will start all AI Assistant services in separate windows:
echo.
echo   [1] ChatBot                Port 5000  - Multi-Model AI Chat + Voice + OCR
echo   [2] Stable Diffusion       Port 7861  - Image Generation
echo   [3] Edit Image             Port 8100  - AI Image Editing (ComfyUI)
echo   [4] MCP Server             stdio      - AI Tools Protocol
echo.
echo ================================================================================
echo.
echo NOTE: Each service will open in a new window.
echo       You can close individual services by closing their windows.
echo.

REM Check Python version first
call "%~dp0check-python.bat"
echo.

REM Setup virtual environment and dependencies
echo Checking virtual environment and dependencies...
call "%~dp0setup-venv.bat"
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to setup environment
    pause
    exit /b 1
)

echo.
pause

echo.
echo [1/4] Starting ChatBot Service...
start "ChatBot Service - Port 5000" cmd /k "%~dp0start-chatbot.bat"
timeout /t 2 >nul

echo [2/4] Starting Stable Diffusion...
start "Stable Diffusion - Port 7861" cmd /k "%~dp0start-stable-diffusion.bat"
timeout /t 2 >nul

echo [3/4] Starting Edit Image...
start "Edit Image - Port 8100" cmd /k "%~dp0start-edit-image.bat"
timeout /t 2 >nul

echo [4/4] Starting MCP Server...
start "MCP Server" cmd /k "%~dp0start-mcp.bat"
timeout /t 2 >nul

echo.
echo ================================================================================
echo   ✅ All Services Started Successfully!
echo ================================================================================
echo.
echo Access the services at:
echo.
echo   ChatBot:                http://localhost:5000
echo   Stable Diffusion:       http://localhost:7861
echo   Edit Image:             http://localhost:8100
echo   MCP Server:             stdio (used by chatbot)
echo.
echo ================================================================================
echo.
echo To stop all services, run: stop-all.bat
echo.
echo Press any key to exit this launcher window...
pause >nul
