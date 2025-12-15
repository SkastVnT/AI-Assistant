@echo off
title AI Assistant - Run All Tests
color 0E

echo ================================================================================
echo.
echo                    AI Assistant Test Suite Runner
echo.
echo ================================================================================
echo.
echo Running comprehensive test suite...
echo.
echo Total Tests: 330+
echo Coverage Target: 85%+
echo.
echo Services Tested:
echo   - Hub Gateway (50 tests)
echo   - ChatBot (40 tests)
echo   - Text2SQL (35 tests)
echo   - Document Intelligence (80 tests)
echo   - Speech2Text (70 tests)
echo   - LoRA Training (40 tests)
echo   - Image Upscale (35 tests)
echo   - Stable Diffusion (40 tests)
echo   - API Integration (30+ tests)
echo.
echo ================================================================================
echo.
pause

echo.
echo Running pytest...
echo.

REM Activate virtual environment if exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
)

REM Run pytest (simple mode without coverage to avoid dependency issues)
pytest tests/ -v

echo.
echo ================================================================================
echo.
echo Test run complete!
echo.
pause
