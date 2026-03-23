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

taskkill /FI "WindowTitle eq ChatBot Service*" /F >nul 2>&1
if %errorlevel% == 0 (echo Stopped ChatBot) else (echo ChatBot not running)

taskkill /FI "WindowTitle eq Stable Diffusion*" /F >nul 2>&1
if %errorlevel% == 0 (echo Stopped Stable Diffusion) else (echo Stable Diffusion not running)

taskkill /FI "WindowTitle eq Edit Image*" /F >nul 2>&1
if %errorlevel% == 0 (echo Stopped Edit Image) else (echo Edit Image not running)

taskkill /FI "WindowTitle eq MCP Server*" /F >nul 2>&1
if %errorlevel% == 0 (echo Stopped MCP Server) else (echo MCP Server not running)

echo.
echo ================================================================================
echo   All services stopped!
echo ================================================================================
echo.
pause
