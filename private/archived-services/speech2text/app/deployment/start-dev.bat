@echo off
REM Docker Development Deployment

cd /d "%~dp0"
cd ..

echo 🛠️ Starting Development Docker Environment...
echo.

docker-compose -f deployment\docker-compose.dev.yml --env-file .env.docker up -d

if %errorlevel% == 0 (
    echo.
    echo [OK] Development services started!
    echo.
    echo [WEB] Access your services:
    echo   - API: http://localhost:8000/docs
    echo   - File Server: http://localhost:8090
    echo   - Redis: localhost:6379
    echo.
    echo 🔄 Hot reload enabled - code changes auto-refresh
    echo [CHART] Check logs with: docker-compose -f deployment\docker-compose.dev.yml logs -f
) else (
    echo.
    echo [ERROR] Failed to start development services
)

pause