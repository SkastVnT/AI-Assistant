@echo off
REM Force UTF-8 encoding to prevent Unicode errors
chcp 65001 >nul 2>&1

title AI Assistant - Service Menu
color 0B

REM Navigate to project root (where menu.bat is located)
cd /d "%~dp0"

:MENU
cls
echo ================================================================================
echo.
echo     █████╗ ██╗    ███████╗███████╗██████╗ ██╗   ██╗██╗ ██████╗███████╗
echo    ██╔══██╗██║    ██╔════╝██╔════╝██╔══██╗██║   ██║██║██╔════╝██╔════╝
echo    ███████║██║    ███████╗█████╗  ██████╔╝██║   ██║██║██║     █████╗  
echo    ██╔══██║██║    ╚════██║██╔══╝  ██╔══██╗╚██╗ ██╔╝██║██║     ██╔══╝  
echo    ██║  ██║██║    ███████║███████╗██║  ██║ ╚████╔╝ ██║╚██████╗███████╗
echo    ╚═╝  ╚═╝╚═╝    ╚══════╝╚══════╝╚═╝  ╚═╝  ╚═══╝  ╚═╝ ╚═════╝╚══════╝
echo.
echo                           Service Manager v2.4
echo ================================================================================
echo.
echo   [SETUP - First Time Users]
echo   0. Quick Setup            (Auto-install everything)
echo.
echo   [SERVICES - Start Individual]
echo   1. Hub Gateway            (Port 3000)
echo   2. ChatBot                (Port 5000)
echo   3. Text2SQL               (Port 5002)
echo   4. Document Intelligence  (Port 5003)
echo   5. Speech2Text            (Port 7860)
echo   6. Stable Diffusion       (Port 7861)
echo   7. LoRA Training          (Port 7862)
echo   8. Image Upscale          (Port 7863)
echo   9. MCP Server             (AI Assistant Protocol)
echo.
echo   [BATCH OPERATIONS]
echo   A. Start ALL Services
echo   S. Stop ALL Services
echo   C. Check Status
echo.
echo   [UTILITIES]
echo   T. Run Tests
echo   H. Health Check ALL (AI-Powered)
echo   L. Activate venv
echo   K. Clean Logs
echo   P. Setup All Services
echo   V. Setup venv for all
echo.
echo   [EXIT]
echo   Q. Quit
echo.
echo ================================================================================
echo.
set /p choice="Select option: "

if /i "%choice%"=="0" start "Quick Setup" cmd /k "scripts\SETUP.bat" & goto MENU
if /i "%choice%"=="1" start "Hub Gateway" cmd /k "scripts\start-hub-gateway.bat" & goto MENU
if /i "%choice%"=="2" start "ChatBot" cmd /k "scripts\start-chatbot.bat" & goto MENU
if /i "%choice%"=="3" start "Text2SQL" cmd /k "scripts\start-text2sql.bat" & goto MENU
if /i "%choice%"=="4" start "Doc Intelligence" cmd /k "scripts\start-document-intelligence.bat" & goto MENU
if /i "%choice%"=="5" start "Speech2Text" cmd /k "scripts\start-speech2text.bat" & goto MENU
if /i "%choice%"=="6" start "Stable Diffusion" cmd /k "scripts\start-stable-diffusion.bat" & goto MENU
if /i "%choice%"=="7" start "LoRA Training" cmd /k "scripts\start-lora-training.bat" & goto MENU
if /i "%choice%"=="8" start "Image Upscale" cmd /k "scripts\start-image-upscale.bat" & goto MENU
if /i "%choice%"=="9" start "MCP Server" cmd /k "scripts\start-mcp.bat" & goto MENU

if /i "%choice%"=="A" start "Start All Services" cmd /k "scripts\start-all.bat" & goto MENU
if /i "%choice%"=="S" start "Stop All Services" cmd /k "scripts\stop-all.bat" & goto MENU
if /i "%choice%"=="C" start "Check Status" cmd /k "scripts\archive\check-status.bat" & goto MENU

if /i "%choice%"=="T" start "Run Tests" cmd /k "scripts\test-all.bat" & goto MENU
if /i "%choice%"=="H" start "Health Check" cmd /k "scripts\health-check-all.bat" & goto MENU
if /i "%choice%"=="L" call .venv\Scripts\activate.bat & exit /b
if /i "%choice%"=="K" start "Clean Logs" cmd /k "scripts\archive\clean-logs.bat" & goto MENU
if /i "%choice%"=="P" start "Setup All Services" cmd /k "scripts\setup-all.bat" & goto MENU
if /i "%choice%"=="V" start "Setup venv" cmd /k "scripts\setup-venv-all.bat" & goto MENU

if /i "%choice%"=="Q" exit

echo.
echo Invalid choice! Please try again...
timeout /t 2 >nul
goto MENU
