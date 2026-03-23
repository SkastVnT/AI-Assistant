@echo off
REM =============================================================================
REM Docker Compose Management Script for Windows
REM =============================================================================

setlocal enabledelayedexpansion

REM Colors (limited in Windows CMD)
set "RED=[91m"
set "GREEN=[92m"
set "YELLOW=[93m"
set "BLUE=[94m"
set "NC=[0m"

goto :main

:print_colored
echo %~2%~1%NC%
goto :eof

:show_help
echo.
echo [MIC] Vietnamese Speech-to-Text Docker Management
echo.
echo Usage: %~nx0 [COMMAND] [OPTIONS]
echo.
echo COMMANDS:
echo   start         Start all services (production)
echo   start-dev     Start development environment
echo   stop          Stop all services
echo   restart       Restart all services
echo   logs          Show logs (all services)
echo   logs SERVICE  Show logs for specific service
echo   status        Show service status
echo   health        Check system health
echo   shell SERVICE Enter shell in service container
echo   build         Build all images
echo   clean         Remove all containers and volumes
echo   update        Pull latest images and restart
echo.
echo SERVICES:
echo   api           Main FastAPI service
echo   t5-service    T5 model service
echo   phowhisper    PhoWhisper service
echo   whisper       Whisper service
echo   gemini        Gemini proxy service
echo   redis         Redis cache
echo   postgres      PostgreSQL database
echo   nginx         Nginx load balancer
echo   health        Health monitor
echo.
echo EXAMPLES:
echo   %~nx0 start                    # Start production environment
echo   %~nx0 start-dev                # Start development environment
echo   %~nx0 logs api                 # Show API logs
echo   %~nx0 shell api                # Enter API container
echo   %~nx0 health                   # Check system health
echo.
goto :eof

:check_requirements
call :print_colored "Checking requirements..." "%BLUE%"

docker --version >nul 2>&1
if errorlevel 1 (
    call :print_colored "Error: Docker is not installed" "%RED%"
    exit /b 1
)

docker-compose --version >nul 2>&1
if errorlevel 1 (
    call :print_colored "Error: Docker Compose is not installed" "%RED%"
    exit /b 1
)

if not exist ".env.docker" (
    call :print_colored "Warning: .env.docker not found, using defaults" "%YELLOW%"
)
goto :eof

:start_production
call :print_colored "Starting production environment..." "%GREEN%"
docker-compose --env-file .env.docker up -d
call :print_colored "Services started! Access at http://localhost" "%GREEN%"
call :print_colored "API Documentation: http://localhost/docs" "%BLUE%"
call :print_colored "Health Monitor: http://localhost/monitoring/" "%BLUE%"
goto :eof

:start_development
call :print_colored "Starting development environment..." "%GREEN%"
docker-compose -f docker-compose.dev.yml --env-file .env.docker up -d
call :print_colored "Development services started!" "%GREEN%"
call :print_colored "API: http://localhost:8000" "%BLUE%"
call :print_colored "File Server: http://localhost:8090" "%BLUE%"
goto :eof

:stop_services
call :print_colored "Stopping all services..." "%YELLOW%"
docker-compose down
docker-compose -f docker-compose.dev.yml down 2>nul
call :print_colored "Services stopped" "%GREEN%"
goto :eof

:restart_services
call :print_colored "Restarting services..." "%YELLOW%"
call :stop_services
timeout /t 2 /nobreak >nul
call :start_production
goto :eof

:show_logs
if "%~1"=="" (
    call :print_colored "Showing all logs..." "%BLUE%"
    docker-compose logs -f
) else (
    call :print_colored "Showing logs for: %~1" "%BLUE%"
    docker-compose logs -f "%~1"
)
goto :eof

:show_status
call :print_colored "Service Status:" "%BLUE%"
docker-compose ps
echo.
call :print_colored "System Resources:" "%BLUE%"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
goto :eof

:check_health
call :print_colored "Checking system health..." "%BLUE%"

curl -s http://localhost/monitoring/health >nul 2>&1
if errorlevel 1 (
    call :print_colored "[ERROR] Health monitor not accessible" "%RED%"
    call :print_colored "Checking individual services..." "%YELLOW%"
    
    call :check_service "api" "8000"
    call :check_service "t5-service" "8001"
    call :check_service "phowhisper-service" "8002"
    call :check_service "whisper-service" "8003"
    call :check_service "grok-proxy" "8004"
) else (
    call :print_colored "[OK] Health monitor is running" "%GREEN%"
    curl -s http://localhost/monitoring/health
)
goto :eof

:check_service
curl -s http://localhost:%~2/health >nul 2>&1
if errorlevel 1 (
    call :print_colored "[ERROR] %~1 is not responding" "%RED%"
) else (
    call :print_colored "[OK] %~1 is healthy" "%GREEN%"
)
goto :eof

:enter_shell
if "%~1"=="" (
    call :print_colored "Error: Please specify service name" "%RED%"
    exit /b 1
)

call :print_colored "Entering shell for: %~1" "%BLUE%"
docker-compose exec "%~1" /bin/bash
goto :eof

:build_images
call :print_colored "Building all images..." "%BLUE%"
docker-compose build --no-cache
call :print_colored "Images built successfully" "%GREEN%"
goto :eof

:clean_all
call :print_colored "Cleaning up all containers and volumes..." "%YELLOW%"
set /p "confirm=This will remove all containers, volumes, and data. Continue? (y/N): "
if /i "!confirm!"=="y" (
    docker-compose down -v --remove-orphans
    docker-compose -f docker-compose.dev.yml down -v --remove-orphans 2>nul
    docker system prune -f
    call :print_colored "Cleanup completed" "%GREEN%"
) else (
    call :print_colored "Cleanup cancelled" "%YELLOW%"
)
goto :eof

:update_services
call :print_colored "Updating services..." "%BLUE%"
docker-compose pull
call :restart_services
call :print_colored "Services updated" "%GREEN%"
goto :eof

:main
if "%~1"=="" goto :show_help
if "%~1"=="help" goto :show_help
if "%~1"=="--help" goto :show_help
if "%~1"=="-h" goto :show_help

if "%~1"=="start" (
    call :check_requirements
    if not errorlevel 1 call :start_production
    goto :end
)

if "%~1"=="start-dev" (
    call :check_requirements
    if not errorlevel 1 call :start_development
    goto :end
)

if "%~1"=="stop" (
    call :stop_services
    goto :end
)

if "%~1"=="restart" (
    call :check_requirements
    if not errorlevel 1 call :restart_services
    goto :end
)

if "%~1"=="logs" (
    call :show_logs "%~2"
    goto :end
)

if "%~1"=="status" (
    call :show_status
    goto :end
)

if "%~1"=="health" (
    call :check_health
    goto :end
)

if "%~1"=="shell" (
    call :enter_shell "%~2"
    goto :end
)

if "%~1"=="build" (
    call :check_requirements
    if not errorlevel 1 call :build_images
    goto :end
)

if "%~1"=="clean" (
    call :clean_all
    goto :end
)

if "%~1"=="update" (
    call :check_requirements
    if not errorlevel 1 call :update_services
    goto :end
)

call :print_colored "Unknown command: %~1" "%RED%"
echo.
call :show_help

:end
endlocal