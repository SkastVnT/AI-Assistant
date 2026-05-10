#!/bin/bash
# =============================================================================
# Start All Services (Except Hub) + Cloudflare Tunnels
# Sau khi chạy xong, copy các URLs và gửi cho AI để update Hub
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

LOGS_DIR="/workspace/AI-Assistant/logs"
mkdir -p "$LOGS_DIR"

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[✓]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}     Starting All Services (Except Hub) + Cloudflare Tunnels${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# =============================================================================
# CLEANUP
# =============================================================================
log_info "Stopping old tunnels and services..."
pkill -f "cloudflared tunnel" 2>/dev/null || true
pkill -f "python.*chatbot_main" 2>/dev/null || true
pkill -f "python.*text2sql.*app" 2>/dev/null || true
pkill -f "uvicorn.*speech" 2>/dev/null || true
pkill -f "python.*upscale" 2>/dev/null || true
sleep 3

# =============================================================================
# START SERVICES
# =============================================================================
echo ""
echo -e "${CYAN}Starting Services...${NC}"
echo ""

# 1. ComfyUI (port 8189)
if ! lsof -i:8189 >/dev/null 2>&1; then
    log_info "Starting ComfyUI on port 8189..."
    cd /workspace/AI-Assistant/ComfyUI
    nohup python main.py --listen 0.0.0.0 --port 8189 > "$LOGS_DIR/comfyui.log" 2>&1 &
    sleep 2
else
    log_warn "ComfyUI already running on 8189"
fi

# 2. Chatbot (port 5000) - includes Document Intelligence
if ! lsof -i:5000 >/dev/null 2>&1; then
    log_info "Starting Chatbot on port 5000..."
    cd /workspace/AI-Assistant/services/chatbot
    nohup python3 chatbot_main.py > "$LOGS_DIR/chatbot.log" 2>&1 &
    sleep 3
else
    log_warn "Chatbot already running on 5000"
fi

# 3. Text2SQL (port 5002)
if ! lsof -i:5002 >/dev/null 2>&1; then
    log_info "Starting Text2SQL on port 5002..."
    cd /workspace/AI-Assistant/services/text2sql
    nohup python3 app.py > "$LOGS_DIR/text2sql.log" 2>&1 &
    sleep 2
else
    log_warn "Text2SQL already running on 5002"
fi

# 4. Speech2Text (port 5001)
if ! lsof -i:5001 >/dev/null 2>&1; then
    log_info "Starting Speech2Text on port 5001..."
    cd /workspace/AI-Assistant/services/speech2text/app/api
    mkdir -p ./audio ./result ./static
    nohup python3 -m uvicorn main:app --host 0.0.0.0 --port 5001 > "$LOGS_DIR/speech2text.log" 2>&1 &
    sleep 3
else
    log_warn "Speech2Text already running on 5001"
fi

# 5. Image Upscale (port 7861)
if ! lsof -i:7861 >/dev/null 2>&1; then
    log_info "Starting Image Upscale on port 7861..."
    cd /workspace/AI-Assistant/services/image-upscale/src
    export PYTHONPATH="/workspace/AI-Assistant/services/image-upscale/src:$PYTHONPATH"
    nohup python3 -m upscale_tool.app > "$LOGS_DIR/image-upscale.log" 2>&1 &
    sleep 2
else
    log_warn "Image Upscale already running on 7861"
fi

log_info "Waiting for services to fully start..."
sleep 5

# =============================================================================
# CHECK SERVICES
# =============================================================================
echo ""
echo -e "${CYAN}Checking Services Status...${NC}"
echo ""

check_service() {
    local name=$1
    local port=$2
    if lsof -i:$port >/dev/null 2>&1; then
        echo -e "  ${GREEN}✅${NC} $name (port $port) - Running"
        return 0
    else
        echo -e "  ${RED}❌${NC} $name (port $port) - Not running"
        return 1
    fi
}

check_service "ComfyUI" 8189
check_service "Chatbot" 5000
check_service "Text2SQL" 5002
check_service "Speech2Text" 5001
check_service "Image Upscale" 7861

# =============================================================================
# START CLOUDFLARE TUNNELS
# =============================================================================
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}           Starting Cloudflare Tunnels${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""

declare -A URLS

start_tunnel() {
    local name=$1
    local port=$2
    local log_file="$LOGS_DIR/tunnel_${name}.log"
    
    if ! lsof -i:$port >/dev/null 2>&1; then
        log_warn "Port $port not listening, skipping tunnel for $name"
        return
    fi
    
    log_info "Creating tunnel for $name (port $port)..."
    rm -f "$log_file"
    nohup cloudflared tunnel --url http://localhost:$port > "$log_file" 2>&1 &
    echo $! > "$LOGS_DIR/tunnel_${name}.pid"
    
    for i in {1..10}; do
        sleep 1
        url=$(grep -o 'https://[a-zA-Z0-9.-]*\.trycloudflare\.com' "$log_file" 2>/dev/null | head -1)
        if [ -n "$url" ]; then
            URLS[$name]=$url
            echo "$url" > "$LOGS_DIR/${name}_public_url.txt"
            log_success "$name: $url"
            return
        fi
    done
    log_warn "$name: Waiting for URL..."
}

start_tunnel "chatbot" 5000
start_tunnel "comfyui" 8189
start_tunnel "text2sql" 5002
start_tunnel "speech2text" 5001
start_tunnel "upscale" 7861

sleep 3

# =============================================================================
# SHOW RESULTS
# =============================================================================
echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}                    PUBLIC URLs${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""

for svc in chatbot comfyui text2sql speech2text upscale; do
    if [ -z "${URLS[$svc]}" ]; then
        url=$(grep -o 'https://[a-zA-Z0-9.-]*\.trycloudflare\.com' "$LOGS_DIR/tunnel_${svc}.log" 2>/dev/null | head -1)
        if [ -n "$url" ]; then
            URLS[$svc]=$url
        fi
    fi
done

for svc in chatbot comfyui text2sql speech2text upscale; do
    if [ -n "${URLS[$svc]}" ]; then
        printf "  %-15s : %s\n" "$svc" "${URLS[$svc]}"
    else
        printf "  %-15s : ${RED}Not available${NC}\n" "$svc"
    fi
done

cat > "$LOGS_DIR/public_urls.json" << EOF
{
    "chatbot": "${URLS[chatbot]:-}",
    "comfyui": "${URLS[comfyui]:-}",
    "text2sql": "${URLS[text2sql]:-}",
    "speech2text": "${URLS[speech2text]:-}",
    "image_upscale": "${URLS[upscale]:-}",
    "timestamp": "$(date -Iseconds)"
}
EOF

echo ""
echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
echo ""
log_success "URLs saved to: $LOGS_DIR/public_urls.json"
echo ""
echo -e "${YELLOW}COPY CAC URLs TREN VA GUI CHO AI DE CAP NHAT HUB GATEWAY!${NC}"
echo ""
