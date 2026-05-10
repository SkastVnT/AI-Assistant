#!/bin/bash
#==========================================================
# 🤖 AI-Assistant Chatbot - Start & Expose to Public
# Chạy chatbot và tạo Cloudflare tunnel để public
# Sử dụng: ./start_chatbot.sh
# Hoặc với nohup để chạy ngay cả khi đóng SSH:
#   nohup ./start_chatbot.sh &
#==========================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Directories
BASE_DIR="/workspace/AI-Assistant"
CHATBOT_DIR="${BASE_DIR}/services/chatbot"
LOGS_DIR="${BASE_DIR}/logs"
URL_FILE="${BASE_DIR}/public_urls.txt"

# Create logs directory
mkdir -p "$LOGS_DIR"

echo -e "${CYAN}╔═══════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║      🤖 AI-Assistant Chatbot Launcher                 ║${NC}"
echo -e "${CYAN}╚═══════════════════════════════════════════════════════╝${NC}"
echo ""

#----------------------------------------------------------
# Function: Find cloudflared binary
#----------------------------------------------------------
find_cloudflared() {
    if command -v cloudflared &> /dev/null; then
        echo "cloudflared"
    elif [[ -f "/opt/instance-tools/bin/cloudflared" ]]; then
        echo "/opt/instance-tools/bin/cloudflared"
    else
        echo ""
    fi
}

#----------------------------------------------------------
# Function: Stop existing processes
#----------------------------------------------------------
stop_existing() {
    echo -e "${YELLOW}🔄 Dừng các process cũ...${NC}"
    pkill -f "python.*chatbot_main.py" 2>/dev/null || true
    pkill -f "cloudflared.*5000" 2>/dev/null || true
    sleep 2
    echo -e "${GREEN}✅ Đã dừng các process cũ${NC}"
}

#----------------------------------------------------------
# Function: Start Chatbot Service
#----------------------------------------------------------
start_chatbot() {
    echo -e "${BLUE}💬 Khởi động Chatbot (port 5000)...${NC}"
    
    cd "$CHATBOT_DIR"
    
    # Start chatbot with nohup
    nohup python3 chatbot_main.py > "${LOGS_DIR}/chatbot.log" 2>&1 &
    CHATBOT_PID=$!
    
    echo -e "   PID: ${GREEN}$CHATBOT_PID${NC}"
    
    # Wait for startup
    echo -e "${YELLOW}   Đang chờ khởi động...${NC}"
    for i in {1..30}; do
        if curl -s --max-time 2 "http://localhost:5000" > /dev/null 2>&1; then
            echo -e "${GREEN}   ✅ Chatbot đã sẵn sàng!${NC}"
            return 0
        fi
        sleep 1
    done
    
    echo -e "${RED}   ❌ Chatbot không khởi động được. Kiểm tra logs:${NC}"
    echo -e "   tail -f ${LOGS_DIR}/chatbot.log"
    return 1
}

#----------------------------------------------------------
# Function: Start Cloudflare Tunnel
#----------------------------------------------------------
start_tunnel() {
    local port=$1
    local name=$2
    local log_file="${LOGS_DIR}/tunnel-${name}.log"
    
    echo -e "${BLUE}🌐 Tạo Cloudflare Tunnel cho ${name} (port ${port})...${NC}"
    
    CLOUDFLARED=$(find_cloudflared)
    
    if [[ -z "$CLOUDFLARED" ]]; then
        echo -e "${RED}❌ cloudflared không tìm thấy!${NC}"
        echo -e "${YELLOW}   Cài đặt: curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared && chmod +x /usr/local/bin/cloudflared${NC}"
        return 1
    fi
    
    # Start tunnel
    nohup $CLOUDFLARED tunnel --url "http://localhost:${port}" > "$log_file" 2>&1 &
    TUNNEL_PID=$!
    
    echo -e "   PID: ${GREEN}$TUNNEL_PID${NC}"
    
    # Wait for tunnel URL
    echo -e "${YELLOW}   Đang chờ URL public...${NC}"
    for i in {1..20}; do
        URL=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" "$log_file" 2>/dev/null | head -1)
        if [[ ! -z "$URL" ]]; then
            echo -e "${GREEN}   ✅ Tunnel sẵn sàng!${NC}"
            echo -e "   🔗 ${CYAN}${URL}${NC}"
            
            # Save URL to file
            grep -v "^${name}:" "$URL_FILE" > "${URL_FILE}.tmp" 2>/dev/null || true
            echo "${name}: ${URL}" >> "${URL_FILE}.tmp"
            mv "${URL_FILE}.tmp" "$URL_FILE"
            
            return 0
        fi
        sleep 1
    done
    
    echo -e "${RED}   ❌ Không lấy được URL tunnel${NC}"
    return 1
}

#----------------------------------------------------------
# Function: Show status
#----------------------------------------------------------
show_status() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                    📊 TRẠNG THÁI                       ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    
    # Check chatbot
    if curl -s --max-time 2 "http://localhost:5000" > /dev/null 2>&1; then
        echo -e "💬 Chatbot (local):  ${GREEN}✅ Đang chạy${NC} - http://localhost:5000"
    else
        echo -e "💬 Chatbot (local):  ${RED}❌ Không chạy${NC}"
    fi
    
    # Show public URLs
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                   🌐 PUBLIC URLs                       ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    
    if [[ -f "$URL_FILE" ]]; then
        while IFS= read -r line; do
            echo -e "🔗 ${GREEN}${line}${NC}"
        done < "$URL_FILE"
    fi
    
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                   📝 LOG FILES                         ${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════${NC}"
    echo -e "📄 Chatbot:        tail -f ${LOGS_DIR}/chatbot.log"
    echo -e "📄 Tunnel:         tail -f ${LOGS_DIR}/tunnel-chatbot.log"
    echo ""
    echo -e "${YELLOW}💡 Tip: Script chạy với nohup, bạn có thể đóng SSH mà không ảnh hưởng${NC}"
    echo ""
}

#----------------------------------------------------------
# MAIN
#----------------------------------------------------------
main() {
    stop_existing
    echo ""
    
    if start_chatbot; then
        echo ""
        start_tunnel 5000 "chatbot"
    fi
    
    show_status
}

# Run main
main
