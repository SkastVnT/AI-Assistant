#!/bin/bash
# =============================================================================
# Stop All Services
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
LOGS_DIR="${PROJECT_ROOT}/logs"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}Stopping all AI-Assistant services...${NC}"
echo ""

# Service ports
declare -A SERVICES=(
    ["hub-gateway"]="3000"
    ["chatbot"]="5000"
    ["speech2text"]="5001"
    ["text2sql"]="5002"
    ["document-intelligence"]="5003"
    ["stable-diffusion"]="7860"
    ["edit-image"]="7861"
    ["lora-training"]="7862"
    ["image-upscale"]="7863"
    ["mcp-server"]="8000"
)

for service in "${!SERVICES[@]}"; do
    port=${SERVICES[$service]}
    pid_file="${LOGS_DIR}/${service}.pid"
    
    # Try PID file first
    if [[ -f "${pid_file}" ]]; then
        pid=$(cat "${pid_file}")
        if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
            kill "${pid}" 2>/dev/null || true
            rm -f "${pid_file}"
            echo -e "${GREEN}✓${NC} Stopped ${service} (PID: ${pid})"
            continue
        fi
        rm -f "${pid_file}"
    fi
    
    # Fallback: kill by port
    pid=$(lsof -t -i:${port} 2>/dev/null | head -1)
    if [[ -n "${pid}" ]]; then
        kill "${pid}" 2>/dev/null || true
        echo -e "${GREEN}✓${NC} Stopped process on port ${port} (PID: ${pid})"
    else
        echo -e "${YELLOW}○${NC} ${service} was not running"
    fi
done

# Stop cloudflared tunnels
echo ""
echo -e "${YELLOW}Stopping cloudflared tunnels...${NC}"
pkill -f cloudflared 2>/dev/null && echo -e "${GREEN}✓${NC} Cloudflared tunnels stopped" || echo -e "${YELLOW}○${NC} No tunnels running"

# Clean up PID files
rm -f "${LOGS_DIR}"/*.pid 2>/dev/null
rm -f "${LOGS_DIR}"/cloudflared_*.pid 2>/dev/null

echo ""
echo -e "${GREEN}All services stopped.${NC}"
