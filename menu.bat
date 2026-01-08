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
echo                           Service Manager v3.0
echo ================================================================================
echo.
echo   [SERVICES]
echo   1. Hub Gateway            (Port 3000)
echo   2. ChatBot                (Port 5000) - Multi-Model AI + SD
echo   3. Text2SQL               (Port 5002)
echo   4. Document Intelligence  (Port 5003)
echo   5. Speech2Text            (Port 5001)
echo   6. Stable Diffusion       (Port 7861)
echo   7. LoRA Training          (Port 7862)
echo   8. Image Upscale          (Port 7863)
echo   9. MCP Server             (Model Context Protocol)
echo   E. Edit Image             (Port 8100) - Grok-like Editor
echo.
echo   [BATCH]
echo   A. Start ALL Services     S. Stop ALL Services
echo.
echo   [SETUP ^& TOOLS]
echo   P. Setup All (First Run)  H. Health Check ALL
echo   T. Run Tests              C. Cleanup Logs/Cache
echo   G. Check GPU              V. Check Python/Venv
echo.
echo   [DEPLOY]
echo   D. Deploy ChatBot         R. Rollback ChatBot
echo.
echo   Q. Quit
echo.
echo ================================================================================
set /p choice="Select: "

if /i "%choice%"=="1" start "Hub Gateway" cmd /k "scripts\start-hub-gateway.bat" & goto MENU
if /i "%choice%"=="2" start "ChatBot" cmd /k "scripts\start-chatbot.bat" & goto MENU
if /i "%choice%"=="3" start "Text2SQL" cmd /k "scripts\start-text2sql.bat" & goto MENU
if /i "%choice%"=="4" start "Doc Intelligence" cmd /k "scripts\start-document-intelligence.bat" & goto MENU
if /i "%choice%"=="5" start "Speech2Text" cmd /k "scripts\start-speech2text.bat" & goto MENU
if /i "%choice%"=="6" start "Stable Diffusion" cmd /k "scripts\start-stable-diffusion.bat" & goto MENU
if /i "%choice%"=="7" start "LoRA Training" cmd /k "scripts\start-lora-training.bat" & goto MENU
if /i "%choice%"=="8" start "Image Upscale" cmd /k "scripts\start-image-upscale.bat" & goto MENU
if /i "%choice%"=="9" start "MCP Server" cmd /k "scripts\start-mcp.bat" & goto MENU
if /i "%choice%"=="E" start "Edit Image" cmd /k "scripts\start-edit-image.bat" & goto MENU

if /i "%choice%"=="A" start "Start All" cmd /k "scripts\start-all.bat" & goto MENU
if /i "%choice%"=="S" start "Stop All" cmd /k "scripts\stop-all.bat" & goto MENU

if /i "%choice%"=="P" start "Setup All" cmd /k "scripts\setup-all.bat" & goto MENU
if /i "%choice%"=="H" start "Health Check" cmd /k "scripts\health-check-all.bat" & goto MENU
if /i "%choice%"=="T" start "Run Tests" cmd /k "scripts\test-all.bat" & goto MENU
if /i "%choice%"=="C" start "Cleanup" cmd /k "scripts\cleanup.bat" & goto MENU
if /i "%choice%"=="G" start "Check GPU" cmd /k "scripts\check-gpu.bat" & goto MENU
if /i "%choice%"=="V" start "Check Python" cmd /k "scripts\check-python.bat" & goto MENU

if /i "%choice%"=="D" start "Deploy ChatBot" cmd /k "scripts\deploy-chatbot.bat" & goto MENU
if /i "%choice%"=="R" start "Rollback ChatBot" cmd /k "scripts\rollback-chatbot.bat" & goto MENU

if /i "%choice%"=="Q" exit

echo Invalid choice!
timeout /t 2 >nul
goto MENU
