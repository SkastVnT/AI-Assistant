#!/bin/bash
# =============================================================================
# Health Check All Services
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
LOGS_DIR="${PROJECT_ROOT}/logs"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
cat << "EOF"
═══════════════════════════════════════════════════════════════════════════════
                         AI-ASSISTANT HEALTH CHECK
═══════════════════════════════════════════════════════════════════════════════
EOF
echo -e "${NC}"

# Service list (name:port:endpoint)
SERVICES="hub-gateway:3000:/health
chatbot:5000:/health
speech2text:5001:/health
text2sql:5002:/health
document-intelligence:5003:/health
stable-diffusion:7860:/sdapi/v1/options
edit-image:7861:/
lora-training:7862:/
image-upscale:7863:/health
mcp-server:8000:/health"

running=0
stopped=0
healthy=0

echo ""

echo "${SERVICES}" | while IFS=: read -r service port endpoint; do
    status_icon=""
    status_text=""
    
    # Check if port is listening
    if netstat -tlnp 2>/dev/null | grep -q ":${port} " || ss -tlnp 2>/dev/null | grep -q ":${port} "; then
        status_icon="${GREEN}●${NC}"
        status_text="${GREEN}RUNNING${NC}"
        
        # Try health endpoint
        health_url="http://localhost:${port}${endpoint}"
        health_response=$(curl -s --max-time 3 "${health_url}" 2>/dev/null || echo "")
        
        if [[ -n "${health_response}" ]]; then
            if echo "${health_response}" | grep -qiE '"status"\s*:\s*"(healthy|ok|running)"' 2>/dev/null; then
                status_text="${GREEN}HEALTHY${NC}"
            elif [[ "${health_response}" != *"error"* ]]; then
                status_text="${GREEN}RESPONDING${NC}"
            fi
        fi
    else
        status_icon="${RED}○${NC}"
        status_text="${RED}STOPPED${NC}"
    fi
    
    # Check for public URL
    url_file="${LOGS_DIR}/${service}_public_url.txt"
    public_url=""
    if [[ -f "${url_file}" ]]; then
        public_url=$(cat "${url_file}")
    fi
    
    printf "  ${status_icon} %-25s Port %-6s [%b]" "${service}" "${port}" "${status_text}"
    
    if [[ -n "${public_url}" ]]; then
        echo -e " → ${CYAN}${public_url}${NC}"
    else
        echo ""
    fi
done

echo ""
echo -e "${CYAN}───────────────────────────────────────────────────────────────────────────────${NC}"

# Count running services
running_count=$(netstat -tlnp 2>/dev/null | grep -cE ":(3000|5000|5001|5002|5003|7860|7861|7862|7863|8000) " || echo "0")
stopped_count=$((10 - running_count))

echo -e "  Summary: ${GREEN}${running_count} running${NC}, ${RED}${stopped_count} stopped${NC}"
echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════════${NC}"
echo ""
