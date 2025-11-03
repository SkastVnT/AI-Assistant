#!/bin/bash

# =============================================================================
# Docker Compose Management Script
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_colored() {
    echo -e "${2}${1}${NC}"
}

show_help() {
    cat << EOF
🎙️ Vietnamese Speech-to-Text Docker Management

Usage: $0 [COMMAND] [OPTIONS]

COMMANDS:
  start         Start all services (production)
  start-dev     Start development environment
  stop          Stop all services
  restart       Restart all services
  logs          Show logs (all services)
  logs SERVICE  Show logs for specific service
  status        Show service status
  health        Check system health
  shell SERVICE Enter shell in service container
  build         Build all images
  clean         Remove all containers and volumes
  update        Pull latest images and restart

SERVICES:
  api           Main FastAPI service
  t5-service    T5 model service
  phowhisper    PhoWhisper service
  whisper       Whisper service
  gemini        Gemini proxy service
  redis         Redis cache
  postgres      PostgreSQL database
  nginx         Nginx load balancer
  health        Health monitor

EXAMPLES:
  $0 start                    # Start production environment
  $0 start-dev                # Start development environment
  $0 logs api                 # Show API logs
  $0 shell api                # Enter API container
  $0 health                   # Check system health

EOF
}

check_requirements() {
    print_colored "Checking requirements..." $BLUE
    
    if ! command -v docker &> /dev/null; then
        print_colored "Error: Docker is not installed" $RED
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_colored "Error: Docker Compose is not installed" $RED
        exit 1
    fi
    
    if [ ! -f ".env.docker" ]; then
        print_colored "Warning: .env.docker not found, using defaults" $YELLOW
    fi
}

start_production() {
    print_colored "Starting production environment..." $GREEN
    docker-compose --env-file .env.docker up -d
    print_colored "Services started! Access at http://localhost" $GREEN
    print_colored "API Documentation: http://localhost/docs" $BLUE
    print_colored "Health Monitor: http://localhost/monitoring/" $BLUE
}

start_development() {
    print_colored "Starting development environment..." $GREEN
    docker-compose -f docker-compose.dev.yml --env-file .env.docker up -d
    print_colored "Development services started!" $GREEN
    print_colored "API: http://localhost:8000" $BLUE
    print_colored "File Server: http://localhost:8090" $BLUE
}

stop_services() {
    print_colored "Stopping all services..." $YELLOW
    docker-compose down
    docker-compose -f docker-compose.dev.yml down 2>/dev/null || true
    print_colored "Services stopped" $GREEN
}

restart_services() {
    print_colored "Restarting services..." $YELLOW
    stop_services
    sleep 2
    start_production
}

show_logs() {
    if [ -z "$1" ]; then
        print_colored "Showing all logs..." $BLUE
        docker-compose logs -f
    else
        print_colored "Showing logs for: $1" $BLUE
        docker-compose logs -f "$1"
    fi
}

show_status() {
    print_colored "Service Status:" $BLUE
    docker-compose ps
    
    print_colored "\nSystem Resources:" $BLUE
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"
}

check_health() {
    print_colored "Checking system health..." $BLUE
    
    if curl -s http://localhost/monitoring/health > /dev/null; then
        print_colored "✅ Health monitor is running" $GREEN
        curl -s http://localhost/monitoring/health | python -m json.tool
    else
        print_colored "❌ Health monitor not accessible" $RED
        print_colored "Checking individual services..." $YELLOW
        
        services=("api:8000" "t5-service:8001" "phowhisper-service:8002" "whisper-service:8003" "gemini-proxy:8004")
        
        for service in "${services[@]}"; do
            name=$(echo $service | cut -d: -f1)
            port=$(echo $service | cut -d: -f2)
            
            if curl -s http://localhost:$port/health > /dev/null; then
                print_colored "✅ $name is healthy" $GREEN
            else
                print_colored "❌ $name is not responding" $RED
            fi
        done
    fi
}

enter_shell() {
    if [ -z "$1" ]; then
        print_colored "Error: Please specify service name" $RED
        exit 1
    fi
    
    print_colored "Entering shell for: $1" $BLUE
    docker-compose exec "$1" /bin/bash
}

build_images() {
    print_colored "Building all images..." $BLUE
    docker-compose build --no-cache
    print_colored "Images built successfully" $GREEN
}

clean_all() {
    print_colored "Cleaning up all containers and volumes..." $YELLOW
    read -p "This will remove all containers, volumes, and data. Continue? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        docker-compose down -v --remove-orphans
        docker-compose -f docker-compose.dev.yml down -v --remove-orphans 2>/dev/null || true
        docker system prune -f
        print_colored "Cleanup completed" $GREEN
    else
        print_colored "Cleanup cancelled" $YELLOW
    fi
}

update_services() {
    print_colored "Updating services..." $BLUE
    docker-compose pull
    restart_services
    print_colored "Services updated" $GREEN
}

# Main script logic
case "${1:-help}" in
    start)
        check_requirements
        start_production
        ;;
    start-dev)
        check_requirements
        start_development
        ;;
    stop)
        stop_services
        ;;
    restart)
        check_requirements
        restart_services
        ;;
    logs)
        show_logs "$2"
        ;;
    status)
        show_status
        ;;
    health)
        check_health
        ;;
    shell)
        enter_shell "$2"
        ;;
    build)
        check_requirements
        build_images
        ;;
    clean)
        clean_all
        ;;
    update)
        check_requirements
        update_services
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_colored "Unknown command: $1" $RED
        echo
        show_help
        exit 1
        ;;
esac