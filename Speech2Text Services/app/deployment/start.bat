@echo off
REM Docker Production Deployment

cd /d "%~dp0"
cd ..

echo 🐳 Starting Production Docker Environment...
echo.

docker-compose -f deployment\docker-compose.yml --env-file .env.docker up -d

if %errorlevel% == 0 (
    echo.
    echo [OK] Services started successfully!
    echo.
    echo [WEB] Access your services:
    echo   - API Documentation: http://localhost/docs
    echo   - Health Monitor: http://localhost/monitoring/
    echo   - Main API: http://localhost/
    echo.
    echo [CHART] Check status with: deployment\health.bat
) else (
    echo.
    echo [ERROR] Failed to start services
    echo Check logs with: docker-compose logs
)

pause