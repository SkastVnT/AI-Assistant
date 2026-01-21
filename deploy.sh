#!/bin/bash
# =============================================================================
# AI-Assistant Deployment Script v2.0
# Complete deployment for local and public environments
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Directories
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICES_DIR="${PROJECT_ROOT}/services"
LOGS_DIR="${PROJECT_ROOT}/logs"
COMFYUI_DIR="/workspace/ComfyUI"

# Create logs directory
mkdir -p "${LOGS_DIR}"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }

check_port() {
    local port=$1
    if ss -tlnp 2>/dev/null | grep -q ":${port} " || netstat -tlnp 2>/dev/null | grep -q ":${port} "; then
        return 0
    fi
    return 1
}

wait_for_port() {
    local port=$1
    local timeout=${2:-30}
    local count=0
    while ! check_port "$port" && [ $count -lt $timeout ]; do
        sleep 1
        ((count++))
    done
    check_port "$port"
}

kill_port() {
    local port=$1
    local pids=$(lsof -t -i:${port} 2>/dev/null)
    if [ -n "$pids" ]; then
        echo "$pids" | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
}

# =============================================================================
# COMFYUI FUNCTIONS
# =============================================================================

start_comfyui() {
    local port=${1:-8189}
    
    log_info "Starting ComfyUI on port $port..."
    
    if check_port "$port"; then
        log_warn "ComfyUI already running on port $port"
        return 0
    fi
    
    cd "$COMFYUI_DIR"
    
    # Start ComfyUI with GPU
    nohup python3 main.py \
        --listen 0.0.0.0 \
        --port "$port" \
        --enable-cors-header \
        --preview-method auto \
        > "${LOGS_DIR}/comfyui.log" 2>&1 &
    
    echo $! > "${LOGS_DIR}/comfyui.pid"
    
    log_info "Waiting for ComfyUI to start..."
    if wait_for_port "$port" 60; then
        log_success "ComfyUI started on port $port"
    else
        log_error "ComfyUI failed to start. Check ${LOGS_DIR}/comfyui.log"
        return 1
    fi
    
    cd "$PROJECT_ROOT"
}

stop_comfyui() {
    log_info "Stopping ComfyUI..."
    kill_port 8189
    pkill -f "python.*main.py.*--port 8189" 2>/dev/null || true
    rm -f "${LOGS_DIR}/comfyui.pid"
    log_success "ComfyUI stopped"
}

# =============================================================================
# GENERIC SERVICE FUNCTIONS
# =============================================================================

start_service() {
    local name=$1
    local port=$2
    local script=$3
    local dir="${SERVICES_DIR}/${name}"
    
    log_info "Starting $name on port $port..."
    
    if check_port "$port"; then
        log_warn "$name already running on port $port"
        return 0
    fi
    
    if [ ! -d "$dir" ]; then
        log_error "Service directory not found: $dir"
        return 1
    fi
    
    cd "$dir"
    
    # Ensure .env exists
    if [ ! -f ".env" ]; then
        cp "${PROJECT_ROOT}/.env" .env 2>/dev/null || true
    fi
    
    nohup python3 "$script" > "${LOGS_DIR}/${name}.log" 2>&1 &
    echo $! > "${LOGS_DIR}/${name}.pid"
    
    log_info "Waiting for $name to start..."
    if wait_for_port "$port" 30; then
        log_success "$name started on port $port"
    else
        log_warn "$name may need more time. Check ${LOGS_DIR}/${name}.log"
    fi
    
    cd "$PROJECT_ROOT"
}

stop_service() {
    local name=$1
    local port=$2
    local process_pattern=$3
    
    log_info "Stopping $name..."
    kill_port "$port"
    pkill -f "$process_pattern" 2>/dev/null || true
    rm -f "${LOGS_DIR}/${name}.pid"
    log_success "$name stopped"
}

# =============================================================================
# INDIVIDUAL SERVICE STARTERS
# =============================================================================

start_hub_gateway() {
    start_service "hub-gateway" 3000 "hub.py"
}

start_chatbot() {
    start_service "chatbot" 5000 "chatbot_main.py"
}

start_speech2text() {
    local port=5001
    local name="speech2text"
    local dir="${SERVICES_DIR}/${name}/app/api"
    
    log_info "Starting $name on port $port..."
    
    if check_port "$port"; then
        log_warn "$name already running on port $port"
        return 0
    fi
    
    cd "$dir"
    
    # Ensure .env exists
    if [ ! -f ".env" ]; then
        cp "${PROJECT_ROOT}/.env" .env 2>/dev/null || true
    fi
    
    # FastAPI runs with uvicorn
    PORT=$port nohup python3 -m uvicorn main:app --host 0.0.0.0 --port $port > "${LOGS_DIR}/${name}.log" 2>&1 &
    echo $! > "${LOGS_DIR}/${name}.pid"
    
    if wait_for_port "$port" 30; then
        log_success "$name started on port $port"
    else
        log_warn "$name may need more time. Check ${LOGS_DIR}/${name}.log"
    fi
    
    cd "$PROJECT_ROOT"
}

start_text2sql() {
    start_service "text2sql" 5002 "app.py"
}

start_document_intelligence() {
    start_service "document-intelligence" 5004 "app.py"
}

start_image_upscale() {
    local port=7861
    local name="image-upscale"
    local dir="${SERVICES_DIR}/${name}/src/upscale_tool"
    
    log_info "Starting $name (Gradio) on port $port..."
    
    if check_port "$port"; then
        log_warn "$name already running on port $port"
        return 0
    fi
    
    cd "$dir"
    
    # Ensure .env exists
    if [ ! -f ".env" ]; then
        cp "${PROJECT_ROOT}/.env" .env 2>/dev/null || true
    fi
    
    nohup python3 app.py > "${LOGS_DIR}/${name}.log" 2>&1 &
    echo $! > "${LOGS_DIR}/${name}.pid"
    
    if wait_for_port "$port" 30; then
        log_success "$name started on port $port"
    else
        log_warn "$name may need more time. Check ${LOGS_DIR}/${name}.log"
    fi
    
    cd "$PROJECT_ROOT"
}

# =============================================================================
# STOP FUNCTIONS
# =============================================================================

stop_hub_gateway() {
    stop_service "hub-gateway" 3000 "python.*hub.py"
}

stop_chatbot() {
    stop_service "chatbot" 5000 "python.*chatbot_main.py"
}

stop_speech2text() {
    stop_service "speech2text" 5001 "python.*speech2text.*app.py"
}

stop_text2sql() {
    stop_service "text2sql" 5002 "python.*text2sql.*app.py"
}

stop_document_intelligence() {
    stop_service "document-intelligence" 5004 "python.*document.*app.py"
}

stop_image_upscale() {
    stop_service "image-upscale" 7861 "python.*upscale.*app.py"
}

# =============================================================================
# MCP SERVER FUNCTIONS
# =============================================================================

start_mcp_server() {
    local port=8000
    
    log_info "Starting MCP Server on port $port..."
    
    if check_port "$port"; then
        log_warn "MCP Server already running on port $port"
        return 0
    fi
    
    cd "${SERVICES_DIR}/mcp-server"
    
    nohup python3 server.py > "${LOGS_DIR}/mcp-server.log" 2>&1 &
    echo $! > "${LOGS_DIR}/mcp-server.pid"
    
    if wait_for_port "$port" 20; then
        log_success "MCP Server started on port $port"
    else
        log_warn "MCP Server may not be fully ready. Check logs."
    fi
    
    cd "$PROJECT_ROOT"
}

stop_mcp_server() {
    log_info "Stopping MCP Server..."
    kill_port 8000
    pkill -f "python.*server.py" 2>/dev/null || true
    rm -f "${LOGS_DIR}/mcp-server.pid"
    log_success "MCP Server stopped"
}

# =============================================================================
# PUBLIC EXPOSURE (CLOUDFLARED)
# =============================================================================

get_cloudflared() {
    if command -v cloudflared &> /dev/null; then
        echo "cloudflared"
    elif [ -f "/opt/instance-tools/bin/cloudflared" ]; then
        echo "/opt/instance-tools/bin/cloudflared"
    elif [ -f "/tmp/cloudflared" ]; then
        echo "/tmp/cloudflared"
    else
        log_info "Downloading cloudflared..."
        curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /tmp/cloudflared
        chmod +x /tmp/cloudflared
        echo "/tmp/cloudflared"
    fi
}

expose_service() {
    local name=$1
    local port=$2
    local cloudflared=$(get_cloudflared)
    
    log_info "Exposing $name (port $port) via Cloudflared..."
    
    # Kill existing tunnel for this service
    pkill -f "cloudflared.*--url.*:${port}" 2>/dev/null || true
    sleep 1
    
    # Start tunnel
    nohup "$cloudflared" tunnel --url "http://localhost:${port}" \
        > "${LOGS_DIR}/cloudflared_${name}.log" 2>&1 &
    
    echo $! > "${LOGS_DIR}/cloudflared_${name}.pid"
    
    # Wait and extract URL
    sleep 5
    local url=$(grep -o 'https://[a-zA-Z0-9-]*\.trycloudflare\.com' "${LOGS_DIR}/cloudflared_${name}.log" 2>/dev/null | head -1)
    
    if [ -n "$url" ]; then
        log_success "$name exposed at: $url"
        echo "$url" > "${LOGS_DIR}/${name}_public_url.txt"
        echo "$url"
    else
        log_warn "Could not extract URL. Check ${LOGS_DIR}/cloudflared_${name}.log"
    fi
}

stop_tunnels() {
    log_info "Stopping all Cloudflared tunnels..."
    pkill -f cloudflared 2>/dev/null || true
    rm -f "${LOGS_DIR}/cloudflared_*.pid"
    log_success "All tunnels stopped"
}

# =============================================================================
# DEPLOYMENT MODES
# =============================================================================

deploy_local() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}          LOCAL DEPLOYMENT (Image Generation Only)${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Start ComfyUI for local image generation
    start_comfyui 8189
    
    echo ""
    echo -e "${GREEN}Local services:${NC}"
    echo "  - ComfyUI: http://localhost:8189"
    echo ""
}

deploy_full() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}              FULL DEPLOYMENT (All Services)${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # 1. Start ComfyUI first (image generation backend)
    start_comfyui 8189
    sleep 2
    
    # 2. Start MCP Server
    start_mcp_server
    sleep 1
    
    # 3. Start all main services
    start_chatbot
    start_speech2text
    start_text2sql
    start_document_intelligence
    start_image_upscale
    
    # 4. Start Hub Gateway LAST (it needs other services running)
    sleep 2
    start_hub_gateway
    
    echo ""
    log_success "All services started!"
    echo ""
    echo -e "${GREEN}Local URLs:${NC}"
    echo "  - Hub Gateway:            http://localhost:3000"
    echo "  - Chatbot:                http://localhost:5000"
    echo "  - Speech2Text:            http://localhost:5001"
    echo "  - Text2SQL:               http://localhost:5002"
    echo "  - Document Intelligence:  http://localhost:5004"
    echo "  - Image Upscale:          http://localhost:7861"
    echo "  - ComfyUI:                http://localhost:8189"
    echo "  - MCP Server:             http://localhost:8000"
    echo ""
}

deploy_public() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}         PUBLIC DEPLOYMENT (With Cloudflare Tunnels)${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # First deploy all services locally
    deploy_full
    
    echo ""
    log_info "Creating public tunnels..."
    echo ""
    
    # Expose main services - Hub first (most important)
    expose_service "hub-gateway" 3000
    expose_service "chatbot" 5000
    expose_service "speech2text" 5001
    expose_service "text2sql" 5002
    expose_service "document-intelligence" 5004
    expose_service "image-upscale" 7861
    expose_service "comfyui" 8189
    
    sleep 3
    
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}                    PUBLIC URLs${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Display all URLs
    for svc in hub-gateway chatbot speech2text text2sql document-intelligence image-upscale comfyui; do
        local url_file="${LOGS_DIR}/${svc}_public_url.txt"
        if [ -f "$url_file" ]; then
            printf "  %-25s : %s\n" "$svc" "$(cat $url_file)"
        fi
    done
    
    echo ""
    
    # Save all URLs to JSON
    cat > "${LOGS_DIR}/public_urls.json" << EOF
{
    "hub_gateway": "$(cat ${LOGS_DIR}/hub-gateway_public_url.txt 2>/dev/null || echo '')",
    "chatbot": "$(cat ${LOGS_DIR}/chatbot_public_url.txt 2>/dev/null || echo '')",
    "speech2text": "$(cat ${LOGS_DIR}/speech2text_public_url.txt 2>/dev/null || echo '')",
    "text2sql": "$(cat ${LOGS_DIR}/text2sql_public_url.txt 2>/dev/null || echo '')",
    "document_intelligence": "$(cat ${LOGS_DIR}/document-intelligence_public_url.txt 2>/dev/null || echo '')",
    "image_upscale": "$(cat ${LOGS_DIR}/image-upscale_public_url.txt 2>/dev/null || echo '')",
    "comfyui": "$(cat ${LOGS_DIR}/comfyui_public_url.txt 2>/dev/null || echo '')",
    "timestamp": "$(date -Iseconds)"
}
EOF
    
    log_success "URLs saved to ${LOGS_DIR}/public_urls.json"
    echo ""
    echo -e "${YELLOW}IMPORTANT:${NC} Hub Gateway will auto-detect and use these public URLs."
    echo ""
}

stop_all() {
    echo ""
    echo -e "${YELLOW}Stopping all services...${NC}"
    echo ""
    
    stop_tunnels
    stop_hub_gateway
    stop_chatbot
    stop_speech2text
    stop_text2sql
    stop_document_intelligence
    stop_image_upscale
    stop_mcp_server
    stop_comfyui
    
    # Kill any remaining python processes for our services
    pkill -f "python.*chatbot_main" 2>/dev/null || true
    pkill -f "python.*hub.py" 2>/dev/null || true
    pkill -f "python.*server.py" 2>/dev/null || true
    pkill -f "python.*main.py.*8189" 2>/dev/null || true
    
    echo ""
    log_success "All services stopped!"
}

status() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                    SERVICE STATUS${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    local services=(
        "Hub-Gateway:3000"
        "Chatbot:5000"
        "Speech2Text:5001"
        "Text2SQL:5002"
        "Document-Intelligence:5004"
        "Image-Upscale:7861"
        "MCP-Server:8000"
        "ComfyUI:8189"
    )
    
    for svc in "${services[@]}"; do
        local name="${svc%%:*}"
        local port="${svc##*:}"
        
        if check_port "$port"; then
            echo -e "  ${GREEN}●${NC} $name (port $port) - ${GREEN}RUNNING${NC}"
        else
            echo -e "  ${RED}○${NC} $name (port $port) - ${RED}STOPPED${NC}"
        fi
    done
    
    echo ""
    
    # Show public URLs if available
    if [ -f "${LOGS_DIR}/public_urls.json" ]; then
        echo -e "${CYAN}Public URLs:${NC}"
        cat "${LOGS_DIR}/public_urls.json" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for k, v in data.items():
    if k != 'timestamp' and v:
        print(f'  {k}: {v}')
" 2>/dev/null || true
        echo ""
    fi
}

# =============================================================================
# MAIN
# =============================================================================

show_help() {
    echo ""
    echo -e "${CYAN}AI-Assistant Deployment Script${NC}"
    echo ""
    echo "Usage: $0 <command>"
    echo ""
    echo "Commands:"
    echo "  local     - Start only ComfyUI for local image generation"
    echo "  full      - Start all services locally (Chatbot + ComfyUI + MCP)"
    echo "  public    - Start all services and expose via Cloudflare"
    echo "  stop      - Stop all services and tunnels"
    echo "  status    - Show status of all services"
    echo "  restart   - Stop and start all services"
    echo ""
    echo "Examples:"
    echo "  $0 local      # Just start ComfyUI for image generation"
    echo "  $0 full       # Start everything locally"
    echo "  $0 public     # Start everything and make public"
    echo "  $0 stop       # Stop everything"
    echo ""
}

case "${1:-}" in
    "local")
        deploy_local
        ;;
    "full")
        deploy_full
        ;;
    "public")
        deploy_public
        ;;
    "stop")
        stop_all
        ;;
    "status")
        status
        ;;
    "restart")
        stop_all
        sleep 2
        deploy_full
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        show_help
        ;;
esac
