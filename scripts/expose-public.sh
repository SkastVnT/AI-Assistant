#!/bin/bash
# =============================================================================
# Expose Services to Public via Cloudflared
# Creates free tunnels for all running services
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
LOGS_DIR="${PROJECT_ROOT}/logs"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

mkdir -p "${LOGS_DIR}"

echo -e "${BLUE}"
cat << "EOF"
═══════════════════════════════════════════════════════════════════════════════
                    EXPOSING SERVICES TO PUBLIC
                         via Cloudflared Tunnels
═══════════════════════════════════════════════════════════════════════════════
EOF
echo -e "${NC}"

# Find cloudflared
CLOUDFLARED=""
if command -v cloudflared &> /dev/null; then
    CLOUDFLARED="cloudflared"
elif [[ -f "/opt/instance-tools/bin/cloudflared" ]]; then
    CLOUDFLARED="/opt/instance-tools/bin/cloudflared"
elif [[ -f "/tmp/cloudflared" ]]; then
    CLOUDFLARED="/tmp/cloudflared"
else
    echo -e "${YELLOW}Downloading cloudflared...${NC}"
    curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /tmp/cloudflared
    chmod +x /tmp/cloudflared
    CLOUDFLARED="/tmp/cloudflared"
fi

echo -e "${GREEN}Using cloudflared: ${CLOUDFLARED}${NC}"
echo ""

# Kill existing tunnels
echo -e "${YELLOW}Stopping any existing tunnels...${NC}"
pkill -f cloudflared 2>/dev/null || true
sleep 2

# Services to expose (customize as needed)
declare -A SERVICES_TO_EXPOSE=(
    ["hub-gateway"]="3000"
    ["chatbot"]="5000"
)

# Optional: Add more services
read -p "Expose additional services? (y/n): " expose_more
if [[ "${expose_more}" == "y" ]]; then
    echo "Select additional services to expose:"
    echo "  1. Document Intelligence (5003)"
    echo "  2. Text2SQL (5002)"
    echo "  3. Speech2Text (5001)"
    echo "  4. Edit Image (7861)"
    echo "  5. All above"
    read -p "Enter numbers (comma-separated, e.g., 1,3): " selections
    
    if [[ "${selections}" == *"5"* ]] || [[ "${selections}" == *"1"* ]]; then
        SERVICES_TO_EXPOSE["document-intelligence"]="5003"
    fi
    if [[ "${selections}" == *"5"* ]] || [[ "${selections}" == *"2"* ]]; then
        SERVICES_TO_EXPOSE["text2sql"]="5002"
    fi
    if [[ "${selections}" == *"5"* ]] || [[ "${selections}" == *"3"* ]]; then
        SERVICES_TO_EXPOSE["speech2text"]="5001"
    fi
    if [[ "${selections}" == *"5"* ]] || [[ "${selections}" == *"4"* ]]; then
        SERVICES_TO_EXPOSE["edit-image"]="7861"
    fi
fi

echo ""
echo -e "${CYAN}Creating tunnels for ${#SERVICES_TO_EXPOSE[@]} services...${NC}"
echo ""

declare -A PUBLIC_URLS

for service in "${!SERVICES_TO_EXPOSE[@]}"; do
    port=${SERVICES_TO_EXPOSE[$service]}
    log_file="${LOGS_DIR}/cloudflared_${service}.log"
    
    # Check if service is running
    if ! (netstat -tlnp 2>/dev/null | grep -q ":${port} " || ss -tlnp 2>/dev/null | grep -q ":${port} "); then
        echo -e "${YELLOW}⚠ ${service} is not running on port ${port}. Starting it...${NC}"
        if [[ -f "${SCRIPT_DIR}/start-${service}.sh" ]]; then
            bash "${SCRIPT_DIR}/start-${service}.sh"
            sleep 3
        else
            echo -e "${RED}✗ Cannot start ${service} - script not found${NC}"
            continue
        fi
    fi
    
    echo -e "${BLUE}Creating tunnel for ${service} (port ${port})...${NC}"
    
    # Start tunnel
    nohup "${CLOUDFLARED}" tunnel --url "http://localhost:${port}" > "${log_file}" 2>&1 &
    pid=$!
    echo "${pid}" > "${LOGS_DIR}/cloudflared_${service}.pid"
    
    # Wait for URL
    sleep 5
    
    # Extract public URL
    public_url=$(grep -o 'https://[^[:space:]]*\.trycloudflare\.com' "${log_file}" 2>/dev/null | head -1)
    
    if [[ -n "${public_url}" ]]; then
        PUBLIC_URLS[$service]="${public_url}"
        echo "${public_url}" > "${LOGS_DIR}/${service}_public_url.txt"
        echo -e "${GREEN}✓ ${service}: ${public_url}${NC}"
    else
        echo -e "${YELLOW}⏳ ${service}: Tunnel starting... (check ${log_file})${NC}"
    fi
    
    sleep 2
done

echo ""
echo -e "${GREEN}"
cat << "EOF"
═══════════════════════════════════════════════════════════════════════════════
                         PUBLIC URLS SUMMARY
═══════════════════════════════════════════════════════════════════════════════
EOF
echo -e "${NC}"

echo ""
for service in "${!PUBLIC_URLS[@]}"; do
    url=${PUBLIC_URLS[$service]}
    printf "  ${GREEN}●${NC} %-25s → ${CYAN}%s${NC}\n" "${service}" "${url}"
done

# Check for any services that might have delayed URL assignment
sleep 3
for service in "${!SERVICES_TO_EXPOSE[@]}"; do
    if [[ -z "${PUBLIC_URLS[$service]}" ]]; then
        log_file="${LOGS_DIR}/cloudflared_${service}.log"
        public_url=$(grep -o 'https://[^[:space:]]*\.trycloudflare\.com' "${log_file}" 2>/dev/null | head -1)
        if [[ -n "${public_url}" ]]; then
            PUBLIC_URLS[$service]="${public_url}"
            echo "${public_url}" > "${LOGS_DIR}/${service}_public_url.txt"
            printf "  ${GREEN}●${NC} %-25s → ${CYAN}%s${NC}\n" "${service}" "${public_url}"
        fi
    fi
done

echo ""
echo -e "${CYAN}───────────────────────────────────────────────────────────────────────────────${NC}"
echo ""
echo -e "${YELLOW}Notes:${NC}"
echo "  • URLs are temporary (free tier) - change on restart"
echo "  • For permanent URLs, create a Cloudflare account and use named tunnels"
echo "  • To stop tunnels: pkill -f cloudflared"
echo "  • Logs: ${LOGS_DIR}/cloudflared_*.log"
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════════${NC}"

# Save summary
cat > "${LOGS_DIR}/public_urls_summary.txt" << EOF
AI-Assistant Public URLs
Generated: $(date)
================================

EOF

for service in "${!PUBLIC_URLS[@]}"; do
    echo "${service}: ${PUBLIC_URLS[$service]}" >> "${LOGS_DIR}/public_urls_summary.txt"
done

echo ""
echo -e "${GREEN}Summary saved to: ${LOGS_DIR}/public_urls_summary.txt${NC}"
