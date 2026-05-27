#!/bin/bash
#===============================================================================
# AI-Assistant Public Deployment Script
# Quick start script to deploy all services with public ngrok URLs
#===============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
LOG_DIR="$PROJECT_ROOT/logs"

# Create log directory
mkdir -p "$LOG_DIR"

# Service configurations (name:port:dir:command)
declare -A SERVICES
SERVICES=(
    ["hub-gateway"]="3000:services/hub-gateway:python3 hub.py"
    ["chatbot"]="5000:services/chatbot:python3 run.py"
    ["document-intelligence"]="5003:services/document-intelligence:python3 run.py"
    ["speech2text"]="5001:services/speech2text/app:python3 web_ui.py"
    ["edit-image"]="8100:services/edit-image:python3 run_grok_ui.py"
)

# PID file
PID_FILE="$PROJECT_ROOT/.deploy_pids"

print_banner() {
    echo -e "${CYAN}"
    echo "â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—"
    echo "â•‘                                                                              â•‘"
    echo "â•‘   â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•— â–ˆâ–ˆâ•—    â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•— â–ˆâ–ˆâ•—   â–ˆâ–ˆâ•—â–ˆâ–ˆâ•— â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—        â•‘"
    echo "â•‘  â–ˆâ–ˆâ•”â•â•â–ˆâ–ˆâ•—â–ˆâ–ˆâ•‘    â–ˆâ–ˆâ•”â•â•â•â•â•â–ˆâ–ˆâ•”â•â•â•â•â•â–ˆâ–ˆâ•”â•â•â–ˆâ–ˆâ•—â–ˆâ–ˆâ•‘   â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•”â•â•â•â•â•â–ˆâ–ˆâ•”â•â•â•â•â•        â•‘"
    echo "â•‘  â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘    â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—  â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•”â•â–ˆâ–ˆâ•‘   â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘     â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—          â•‘"
    echo "â•‘  â–ˆâ–ˆâ•”â•â•â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘    â•šâ•â•â•â•â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•”â•â•â•  â–ˆâ–ˆâ•”â•â•â–ˆâ–ˆâ•—â•šâ–ˆâ–ˆâ•— â–ˆâ–ˆâ•”â•â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘     â–ˆâ–ˆâ•”â•â•â•          â•‘"
    echo "â•‘  â–ˆâ–ˆâ•‘  â–ˆâ–ˆâ•‘â–ˆâ–ˆâ•‘    â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•‘â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ•‘  â–ˆâ–ˆâ•‘ â•šâ–ˆâ–ˆâ–ˆâ–ˆâ•”â• â–ˆâ–ˆâ•‘â•šâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—â–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ–ˆâ•—        â•‘"
    echo "â•‘  â•šâ•â•  â•šâ•â•â•šâ•â•    â•šâ•â•â•â•â•â•â•â•šâ•â•â•â•â•â•â•â•šâ•â•  â•šâ•â•  â•šâ•â•â•â•  â•šâ•â• â•šâ•â•â•â•â•â•â•šâ•â•â•â•â•â•â•        â•‘"
    echo "â•‘                                                                              â•‘"
    echo "â•‘                    ðŸŒ Public Deployment Script v1.0 ðŸŒ                       â•‘"
    echo "â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•"
    echo -e "${NC}"
}

check_ngrok() {
    if ! command -v ngrok &> /dev/null; then
        echo -e "${YELLOW}ðŸ“¦ ngrok not found. Installing via pip...${NC}"
        pip install pyngrok -q
        
        # Try to get ngrok path
        if python3 -c "from pyngrok import ngrok; print(ngrok.get_ngrok_process())" 2>/dev/null; then
            echo -e "${GREEN}âœ“ pyngrok installed${NC}"
        else
            echo -e "${RED}âš ï¸  Please install ngrok manually:${NC}"
            echo "   Linux: snap install ngrok"
            echo "   macOS: brew install ngrok"
            echo "   Or download from: https://ngrok.com/download"
            exit 1
        fi
    else
        echo -e "${GREEN}âœ“ ngrok is installed${NC}"
    fi
}

kill_port() {
    local port=$1
    lsof -ti :$port 2>/dev/null | xargs kill -9 2>/dev/null || true
}

wait_for_port() {
    local port=$1
    local timeout=${2:-30}
    local count=0
    
    while [ $count -lt $timeout ]; do
        if lsof -ti :$port &>/dev/null; then
            return 0
        fi
        sleep 1
        ((count++))
    done
    return 1
}

start_service() {
    local name=$1
    local config=${SERVICES[$name]}
    
    if [ -z "$config" ]; then
        echo -e "${RED}âŒ Unknown service: $name${NC}"
        return 1
    fi
    
    IFS=':' read -r port dir command <<< "$config"
    local service_dir="$PROJECT_ROOT/$dir"
    
    if [ ! -d "$service_dir" ]; then
        echo -e "${YELLOW}âš ï¸  Directory not found: $dir${NC}"
        return 1
    fi
    
    echo -e "${BLUE}ðŸš€ Starting $name on port $port...${NC}"
    
    # Kill existing process
    kill_port $port
    sleep 1
    
    # Start service
    cd "$service_dir"
    nohup $command > "$LOG_DIR/$name.log" 2>&1 &
    local pid=$!
    echo "$name:$pid:$port" >> "$PID_FILE"
    
    # Wait for port
    if wait_for_port $port 30; then
        echo -e "${GREEN}   âœ“ $name started (PID: $pid)${NC}"
        return 0
    else
        echo -e "${YELLOW}   âš ï¸  $name may still be starting...${NC}"
        return 0
    fi
}

create_tunnel() {
    local name=$1
    local port=$2
    
    if ! lsof -ti :$port &>/dev/null; then
        echo -e "${YELLOW}   âš ï¸  Port $port not listening, skipping tunnel${NC}"
        return 1
    fi
    
    echo -e "${CYAN}ðŸ”— Creating tunnel for $name (port $port)...${NC}"
    
    # Use pyngrok to create tunnel
    python3 << EOF
from pyngrok import ngrok
import json

try:
    tunnel = ngrok.connect($port, "http")
    print(f"TUNNEL_URL={tunnel.public_url}")
    
    # Save to file
    with open("$PROJECT_ROOT/.tunnels", "a") as f:
        f.write(f"$name:{tunnel.public_url}\n")
except Exception as e:
    print(f"ERROR: {e}")
EOF
}

start_all() {
    echo ""
    echo -e "${BOLD}ðŸ“‹ Starting services...${NC}"
    echo ""
    
    # Clear old files
    rm -f "$PID_FILE" "$PROJECT_ROOT/.tunnels"
    
    local started=0
    local failed=0
    
    for name in "${!SERVICES[@]}"; do
        if start_service "$name"; then
            ((started++))
        else
            ((failed++))
        fi
    done
    
    echo ""
    echo -e "${BOLD}ðŸ”— Creating ngrok tunnels...${NC}"
    echo ""
    
    for name in "${!SERVICES[@]}"; do
        IFS=':' read -r port _ _ <<< "${SERVICES[$name]}"
        create_tunnel "$name" "$port"
    done
    
    echo ""
    return 0
}

show_status() {
    echo ""
    echo -e "${BOLD}â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}"
    printf "${BOLD}%-25s %-8s %-12s %s${NC}\n" "SERVICE" "PORT" "STATUS" "PUBLIC URL"
    echo -e "${BOLD}â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}"
    
    for name in "${!SERVICES[@]}"; do
        IFS=':' read -r port _ _ <<< "${SERVICES[$name]}"
        
        # Check if running
        if lsof -ti :$port &>/dev/null; then
            status="${GREEN}âœ“ ONLINE${NC}"
        else
            status="${RED}âœ— OFFLINE${NC}"
        fi
        
        # Get tunnel URL
        local url="-"
        if [ -f "$PROJECT_ROOT/.tunnels" ]; then
            url=$(grep "^$name:" "$PROJECT_ROOT/.tunnels" 2>/dev/null | cut -d: -f2- || echo "-")
        fi
        
        printf "%-25s %-8s %-22b %s\n" "$name" "$port" "$status" "$url"
    done
    
    echo "â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•"
    echo ""
}

save_urls() {
    if [ -f "$PROJECT_ROOT/.tunnels" ]; then
        echo -e "${GREEN}ðŸ“„ Public URLs:${NC}"
        cat "$PROJECT_ROOT/.tunnels"
        
        # Copy to public_urls.txt
        cp "$PROJECT_ROOT/.tunnels" "$PROJECT_ROOT/public_urls.txt"
        echo -e "${GREEN}ðŸ“„ URLs saved to: $PROJECT_ROOT/public_urls.txt${NC}"
    fi
}

stop_all() {
    echo -e "${YELLOW}ðŸ›‘ Stopping all services...${NC}"
    
    # Kill ngrok
    pkill -f ngrok 2>/dev/null || true
    python3 -c "from pyngrok import ngrok; ngrok.kill()" 2>/dev/null || true
    
    # Kill services
    if [ -f "$PID_FILE" ]; then
        while IFS=: read -r name pid port; do
            kill $pid 2>/dev/null && echo "   Stopped $name (PID: $pid)" || true
        done < "$PID_FILE"
        rm -f "$PID_FILE"
    fi
    
    # Kill by port
    for name in "${!SERVICES[@]}"; do
        IFS=':' read -r port _ _ <<< "${SERVICES[$name]}"
        kill_port $port
    done
    
    rm -f "$PROJECT_ROOT/.tunnels"
    echo -e "${GREEN}âœ“ All services stopped${NC}"
}

cleanup() {
    echo ""
    echo -e "${YELLOW}Received interrupt, cleaning up...${NC}"
    stop_all
    exit 0
}

# Main
main() {
    print_banner
    
    case "${1:-start}" in
        start)
            trap cleanup SIGINT SIGTERM
            check_ngrok
            start_all
            show_status
            save_urls
            echo -e "${GREEN}ðŸŽ‰ All services are running!${NC}"
            echo -e "${YELLOW}Press Ctrl+C to stop all services${NC}"
            echo ""
            # Keep running
            while true; do sleep 1; done
            ;;
        stop)
            stop_all
            ;;
        status)
            show_status
            ;;
        restart)
            stop_all
            sleep 2
            start_all
            show_status
            ;;
        *)
            echo "Usage: $0 {start|stop|status|restart}"
            exit 1
            ;;
    esac
}

main "$@"
