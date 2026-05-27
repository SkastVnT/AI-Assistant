#!/bin/bash
#==========================================================
# ðŸ¤– AI-Assistant Chatbot - Start & Expose to Public
# Cháº¡y chatbot vÃ  táº¡o Cloudflare tunnel Ä‘á»ƒ public
# Sá»­ dá»¥ng: ./start_chatbot.sh
# Hoáº·c vá»›i nohup Ä‘á»ƒ cháº¡y ngay cáº£ khi Ä‘Ã³ng SSH:
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

echo -e "${CYAN}â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—${NC}"
echo -e "${CYAN}â•‘      ðŸ¤– AI-Assistant Chatbot Launcher                 â•‘${NC}"
echo -e "${CYAN}â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}"
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
    echo -e "${YELLOW}ðŸ”„ Dá»«ng cÃ¡c process cÅ©...${NC}"
    pkill -f "python.*chatbot_main.py" 2>/dev/null || true
    pkill -f "cloudflared.*5000" 2>/dev/null || true
    sleep 2
    echo -e "${GREEN}âœ… ÄÃ£ dá»«ng cÃ¡c process cÅ©${NC}"
}

#----------------------------------------------------------
# Function: Start Chatbot Service
#----------------------------------------------------------
start_chatbot() {
    echo -e "${BLUE}ðŸ’¬ Khá»Ÿi Ä‘á»™ng Chatbot (port 5000)...${NC}"
    
    cd "$CHATBOT_DIR"
    
    # Start chatbot with nohup
    nohup python3 chatbot_main.py > "${LOGS_DIR}/chatbot.log" 2>&1 &
    CHATBOT_PID=$!
    
    echo -e "   PID: ${GREEN}$CHATBOT_PID${NC}"
    
    # Wait for startup
    echo -e "${YELLOW}   Äang chá» khá»Ÿi Ä‘á»™ng...${NC}"
    for i in {1..30}; do
        if curl -s --max-time 2 "http://localhost:5000" > /dev/null 2>&1; then
            echo -e "${GREEN}   âœ… Chatbot Ä‘Ã£ sáºµn sÃ ng!${NC}"
            return 0
        fi
        sleep 1
    done
    
    echo -e "${RED}   âŒ Chatbot khÃ´ng khá»Ÿi Ä‘á»™ng Ä‘Æ°á»£c. Kiá»ƒm tra logs:${NC}"
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
    
    echo -e "${BLUE}ðŸŒ Táº¡o Cloudflare Tunnel cho ${name} (port ${port})...${NC}"
    
    CLOUDFLARED=$(find_cloudflared)
    
    if [[ -z "$CLOUDFLARED" ]]; then
        echo -e "${RED}âŒ cloudflared khÃ´ng tÃ¬m tháº¥y!${NC}"
        echo -e "${YELLOW}   CÃ i Ä‘áº·t: curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /usr/local/bin/cloudflared && chmod +x /usr/local/bin/cloudflared${NC}"
        return 1
    fi
    
    # Start tunnel
    nohup $CLOUDFLARED tunnel --url "http://localhost:${port}" > "$log_file" 2>&1 &
    TUNNEL_PID=$!
    
    echo -e "   PID: ${GREEN}$TUNNEL_PID${NC}"
    
    # Wait for tunnel URL
    echo -e "${YELLOW}   Äang chá» URL public...${NC}"
    for i in {1..20}; do
        URL=$(grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" "$log_file" 2>/dev/null | head -1)
        if [[ ! -z "$URL" ]]; then
            echo -e "${GREEN}   âœ… Tunnel sáºµn sÃ ng!${NC}"
            echo -e "   ðŸ”— ${CYAN}${URL}${NC}"
            
            # Save URL to file
            grep -v "^${name}:" "$URL_FILE" > "${URL_FILE}.tmp" 2>/dev/null || true
            echo "${name}: ${URL}" >> "${URL_FILE}.tmp"
            mv "${URL_FILE}.tmp" "$URL_FILE"
            
            return 0
        fi
        sleep 1
    done
    
    echo -e "${RED}   âŒ KhÃ´ng láº¥y Ä‘Æ°á»£c URL tunnel${NC}"
    return 1
}

#----------------------------------------------------------
# Function: Show status
#----------------------------------------------------------
show_status() {
    echo ""
    echo -e "${CYAN}â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}"
    echo -e "${CYAN}                    ðŸ“Š TRáº NG THÃI                       ${NC}"
    echo -e "${CYAN}â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}"
    
    # Check chatbot
    if curl -s --max-time 2 "http://localhost:5000" > /dev/null 2>&1; then
        echo -e "ðŸ’¬ Chatbot (local):  ${GREEN}âœ… Äang cháº¡y${NC} - http://localhost:5000"
    else
        echo -e "ðŸ’¬ Chatbot (local):  ${RED}âŒ KhÃ´ng cháº¡y${NC}"
    fi
    
    # Show public URLs
    echo ""
    echo -e "${CYAN}â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}"
    echo -e "${CYAN}                   ðŸŒ PUBLIC URLs                       ${NC}"
    echo -e "${CYAN}â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}"
    
    if [[ -f "$URL_FILE" ]]; then
        while IFS= read -r line; do
            echo -e "ðŸ”— ${GREEN}${line}${NC}"
        done < "$URL_FILE"
    fi
    
    echo ""
    echo -e "${CYAN}â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}"
    echo -e "${CYAN}                   ðŸ“ LOG FILES                         ${NC}"
    echo -e "${CYAN}â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•${NC}"
    echo -e "ðŸ“„ Chatbot:        tail -f ${LOGS_DIR}/chatbot.log"
    echo -e "ðŸ“„ Tunnel:         tail -f ${LOGS_DIR}/tunnel-chatbot.log"
    echo ""
    echo -e "${YELLOW}ðŸ’¡ Tip: Script cháº¡y vá»›i nohup, báº¡n cÃ³ thá»ƒ Ä‘Ã³ng SSH mÃ  khÃ´ng áº£nh hÆ°á»Ÿng${NC}"
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
