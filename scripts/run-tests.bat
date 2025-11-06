@echo off
REM ============================================================================
REM Quick Test Runner Script for Windows
REM Usage: run-tests.bat [service] [coverage]
REM ============================================================================

echo ======================================
echo AI-Assistant Test Runner (Windows)
echo ======================================

set SERVICE=%1
if "%SERVICE%"=="" set SERVICE=all

set COVERAGE=%2
if "%COVERAGE%"=="" set COVERAGE=yes

REM Check if pytest is installed
python -c "import pytest" 2>nul
if errorlevel 1 (
    echo Installing test dependencies...
    pip install pytest pytest-cov pytest-mock pytest-flask requests-mock
)

REM Run tests based on service
if "%SERVICE%"=="chatbot" goto :chatbot
if "%SERVICE%"=="ChatBot" goto :chatbot
if "%SERVICE%"=="text2sql" goto :text2sql
if "%SERVICE%"=="Text2SQL" goto :text2sql
if "%SERVICE%"=="all" goto :all
goto :unknown

:chatbot
echo.
echo Testing ChatBot...
cd ChatBot
if "%COVERAGE%"=="yes" (
    pytest tests/ -v --cov=. --cov-report=html --cov-report=term-missing
) else (
    pytest tests/ -v
)
cd ..
goto :end

:text2sql
echo.
echo Testing Text2SQL...
cd "Text2SQL Services"
if "%COVERAGE%"=="yes" (
    pytest tests/ -v --cov=. --cov-report=html --cov-report=term-missing
) else (
    pytest tests/ -v
)
cd ..
goto :end

:all
echo.
echo Running all tests...
echo.
call :chatbot
echo.
call :text2sql
goto :end

:unknown
echo Unknown service: %SERVICE%
echo Available services: chatbot, text2sql, all
exit /b 1

:end
echo.
echo ✓ Tests completed!
exit /b 0
