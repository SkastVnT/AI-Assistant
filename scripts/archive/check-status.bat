@echo off
title AI Assistant - Status Check
color 0B

echo ================================================================================
echo.
echo                    AI Assistant Services Status
echo.
echo ================================================================================
echo.

echo Checking service ports...
echo.

REM Function to check if port is listening
powershell -Command "$ports = @(3000, 5001, 5002, 5003, 7860, 7861, 7862, 7863); $services = @('Hub Gateway', 'ChatBot', 'Text2SQL', 'Doc Intelligence', 'Speech2Text', 'Stable Diffusion', 'LoRA Training', 'Image Upscale'); for ($i=0; $i -lt $ports.Length; $i++) { $port = $ports[$i]; $service = $services[$i]; $conn = Test-NetConnection -ComputerName localhost -Port $port -WarningAction SilentlyContinue -InformationLevel Quiet; if ($conn) { Write-Host \"✅ $service (Port $port) - RUNNING\" -ForegroundColor Green } else { Write-Host \"❌ $service (Port $port) - NOT RUNNING\" -ForegroundColor Red } }"

echo.
echo ================================================================================
echo.
echo To start all services: start-all.bat
echo To stop all services:  stop-all.bat
echo.
pause
