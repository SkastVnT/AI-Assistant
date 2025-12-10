@echo off
REM ============================================================================
REM Phase 1: Performance Optimization - Installation Script
REM ============================================================================

echo.
echo ========================================
echo  PHASE 1: Performance Optimization
echo  Installing dependencies...
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv_chatbot" (
    echo [ERROR] Virtual environment not found!
    echo Please run: python -m venv venv_chatbot
    exit /b 1
)

REM Activate virtual environment
call venv_chatbot\Scripts\activate.bat

echo [1/5] Installing Redis...
pip install redis>=5.0.0

echo.
echo [2/5] Installing MongoDB driver...
pip install pymongo>=4.6.0 dnspython>=2.4.0

echo.
echo [3/5] Checking Redis installation...
python -c "import redis; print('✅ Redis installed successfully')" || (
    echo [ERROR] Redis installation failed
    exit /b 1
)

echo.
echo [4/5] Checking MongoDB installation...
python -c "import pymongo; print('✅ MongoDB installed successfully')" || (
    echo [ERROR] MongoDB installation failed
    exit /b 1
)

echo.
echo [5/5] Installing Redis Server (Windows)...
echo.
echo 📦 Please download and install Redis for Windows:
echo    https://github.com/microsoftarchive/redis/releases
echo.
echo    Or use WSL2/Docker:
echo    docker run -d -p 6379:6379 redis:alpine
echo.

echo.
echo ========================================
echo  ✅ Installation Complete!
echo ========================================
echo.
echo Next steps:
echo 1. Update .env file with MongoDB URI
echo 2. Start Redis server (or Docker container)
echo 3. Run: python test_performance.py
echo 4. Run: python app.py
echo.

pause
