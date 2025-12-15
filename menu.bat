@echo off
title AI Assistant - Service Menu
color 0B

REM Check Python version on first run
if not defined PYTHON_CHECKED (
    call scripts\check-python.bat
    set PYTHON_CHECKED=1
    echo.
)

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
echo                           Service Manager v2.3
echo ================================================================================
echo.
echo   [SERVICES - Start Individual]
echo   1. Hub Gateway            (Port 3000)
echo   2. ChatBot                (Port 5001)
echo   3. Text2SQL               (Port 5002)
echo   4. Document Intelligence  (Port 5003)
echo   5. Speech2Text            (Port 7860)
echo   6. Stable Diffusion       (Port 7861)
echo   7. LoRA Training          (Port 7862)
echo   8. Image Upscale          (Port 7863)
echo.
echo   [BATCH OPERATIONS]
echo   A. Start ALL Services
echo   S. Stop ALL Services
echo   C. Check Status
echo.
echo   [UTILITIES]
echo   T. Run Tests
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

if /i "%choice%"=="1" start "Hub Gateway" cmd /k "scripts\start-hub-gateway.bat" & goto MENU
if /i "%choice%"=="2" start "ChatBot" cmd /k "scripts\start-chatbot.bat" & goto MENU
if /i "%choice%"=="3" start "Text2SQL" cmd /k "scripts\start-text2sql.bat" & goto MENU
if /i "%choice%"=="4" start "Doc Intelligence" cmd /k "scripts\start-document-intelligence.bat" & goto MENU
if /i "%choice%"=="5" start "Speech2Text" cmd /k "scripts\start-speech2text.bat" & goto MENU
if /i "%choice%"=="6" start "Stable Diffusion" cmd /k "scripts\start-stable-diffusion.bat" & goto MENU
if /i "%choice%"=="7" start "LoRA Training" cmd /k "scripts\start-lora-training.bat" & goto MENU
if /i "%choice%"=="8" start "Image Upscale" cmd /k "scripts\start-image-upscale.bat" & goto MENU

if /i "%choice%"=="A" call scripts\start-all.bat & goto MENU
if /i "%choice%"=="S" call scripts\stop-all.bat & goto MENU
if /i "%choice%"=="C" call scripts\archive\check-status.bat & goto MENU

if /i "%choice%"=="T" call scripts\test-all.bat & goto MENU
if /i "%choice%"=="L" call .venv\Scripts\activate.bat & exit /b
if /i "%choice%"=="K" call scripts\archive\clean-logs.bat & goto MENU
if /i "%choice%"=="P" call scripts\setup-all.bat & goto MENU
if /i "%choice%"=="V" call scripts\setup-venv-all.bat & goto MENU

if /i "%choice%"=="Q" exit

echo.
echo Invalid choice! Please try again...
timeout /t 2 >nul
goto MENU
