@echo off
REM Health Check Script

cd /d "%~dp0"
cd ..

echo [CHART] System Health Check
echo.

echo 🐳 Docker Containers:
docker ps --filter "name=s2t" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo.
echo [WEB] API Health:
curl -s http://localhost:8000/health 2>nul
if %errorlevel% == 0 (
    echo [OK] API is responding
) else (
    echo [ERROR] API not responding
)

echo.
echo 🔄 Redis Health:
docker exec s2t-redis-test redis-cli ping 2>nul
if %errorlevel% == 0 (
    echo [OK] Redis is responding
) else (
    echo [ERROR] Redis not responding
)

echo.
echo [GROWTH] Resource Usage:
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" --filter "name=s2t"

pause