@echo off
title AI Assistant - Stop All Services
color 0C

REM Navigate to project root (parent of scripts folder)
cd /d "%~dp0.."

echo ================================================================================
echo.
echo                         Stop All AI Services
echo.
echo ================================================================================
echo.
echo This will stop all running AI Assistant services...
echo.
pause

echo.
echo Stopping services by window title...
echo.

taskkill /FI "WindowTitle eq AI Hub Gateway*" /F >nul 2>&1
if %errorlevel% == 0 (echo ✓ Stopped Hub Gateway) else (echo ✗ Hub Gateway not running)

taskkill /FI "WindowTitle eq ChatBot Service*" /F >nul 2>&1
if %errorlevel% == 0 (echo ✓ Stopped ChatBot) else (echo ✗ ChatBot not running)

taskkill /FI "WindowTitle eq Text2SQL Service*" /F >nul 2>&1
if %errorlevel% == 0 (echo ✓ Stopped Text2SQL) else (echo ✗ Text2SQL not running)

taskkill /FI "WindowTitle eq Document Intelligence*" /F >nul 2>&1
if %errorlevel% == 0 (echo ✓ Stopped Document Intelligence) else (echo ✗ Document Intelligence not running)

taskkill /FI "WindowTitle eq Speech2Text Service*" /F >nul 2>&1
if %errorlevel% == 0 (echo ✓ Stopped Speech2Text) else (echo ✗ Speech2Text not running)

taskkill /FI "WindowTitle eq Stable Diffusion*" /F >nul 2>&1
if %errorlevel% == 0 (echo ✓ Stopped Stable Diffusion) else (echo ✗ Stable Diffusion not running)

taskkill /FI "WindowTitle eq LoRA Training*" /F >nul 2>&1
if %errorlevel% == 0 (echo ✓ Stopped LoRA Training) else (echo ✗ LoRA Training not running)

taskkill /FI "WindowTitle eq Image Upscale*" /F >nul 2>&1
if %errorlevel% == 0 (echo ✓ Stopped Image Upscale) else (echo ✗ Image Upscale not running)

echo.
echo ================================================================================
echo   All services stopped!
echo ================================================================================
echo.
pause
