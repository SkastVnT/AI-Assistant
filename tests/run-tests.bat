@echo off
REM ============================================================================
REM AI-Assistant Test Runner
REM Runs all tests with coverage reporting
REM ============================================================================

echo ========================================
echo AI-Assistant Test Suite
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo Please run: python -m venv venv
    echo Then: .\venv\Scripts\activate
    echo And: pip install -r requirements.txt -r requirements-test.txt
    pause
    exit /b 1
)

REM Activate virtual environment
echo [1/5] Activating virtual environment...
call venv\Scripts\activate.bat

REM Install test dependencies
echo.
echo [2/5] Installing test dependencies...
pip install -q -r requirements-test.txt

REM Clear previous coverage data
echo.
echo [3/5] Cleaning previous test results...
if exist .coverage del .coverage
if exist htmlcov rmdir /s /q htmlcov
if exist .pytest_cache rmdir /s /q .pytest_cache

REM Run tests with coverage
echo.
echo [4/5] Running tests...
echo ========================================
pytest -v --cov=src --cov=ChatBot/src --cov-report=html --cov-report=term-missing --cov-branch

REM Check test results
if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo [SUCCESS] All tests passed!
    echo ========================================
) else (
    echo.
    echo ========================================
    echo [WARNING] Some tests failed!
    echo ========================================
)

REM Open coverage report
echo.
echo [5/5] Opening coverage report...
if exist htmlcov\index.html (
    start htmlcov\index.html
    echo Coverage report opened in browser
) else (
    echo Coverage report not found
)

echo.
echo ========================================
echo Test run complete!
echo Coverage report: htmlcov\index.html
echo ========================================
echo.

pause
