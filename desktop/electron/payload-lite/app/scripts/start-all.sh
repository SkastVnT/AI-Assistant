#!/bin/bash
# =============================================================================
# Start All Core Services
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"

# Colors
GREEN='\033[0;32m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
cat << "EOF"
================================================================================
                    STARTING ALL AI-ASSISTANT SERVICES
================================================================================
EOF
echo -e "${NC}"

# Start core services in order
echo -e "${GREEN}[1/5]${NC} Starting Hub Gateway..."
bash "${SCRIPT_DIR}/start-hub-gateway.sh"
sleep 2

echo ""
echo -e "${GREEN}[2/5]${NC} Starting ChatBot..."
bash "${SCRIPT_DIR}/start-chatbot.sh"
sleep 2

echo ""
echo -e "${GREEN}[3/5]${NC} Starting MCP Server..."
bash "${SCRIPT_DIR}/start-mcp-server.sh"
sleep 2

echo ""
echo -e "${GREEN}[4/5]${NC} Starting Document Intelligence..."
bash "${SCRIPT_DIR}/start-document-intelligence.sh"
sleep 2

echo ""
echo -e "${GREEN}[5/5]${NC} Starting Text2SQL..."
bash "${SCRIPT_DIR}/start-text2sql.sh"
sleep 2

echo ""
echo -e "${CYAN}=================================================================================${NC}"
echo -e "${GREEN}All core services started!${NC}"
echo -e "${CYAN}=================================================================================${NC}"
echo ""
echo "Run 'bash scripts/health-check-all.sh' to verify all services"
echo "Run 'bash scripts/expose-public.sh' to expose services via Cloudflared"
