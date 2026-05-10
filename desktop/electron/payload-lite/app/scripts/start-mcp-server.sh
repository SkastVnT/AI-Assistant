#!/bin/bash
# =============================================================================
# Start MCP Server
# Port: 8000
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
SERVICE_DIR="${PROJECT_ROOT}/services/mcp-server"
LOGS_DIR="${PROJECT_ROOT}/logs"
PORT=8000

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

mkdir -p "${LOGS_DIR}"

echo -e "${GREEN}Starting MCP Server on port ${PORT}...${NC}"

# Check if already running
if netstat -tlnp 2>/dev/null | grep -q ":${PORT} " || ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
    echo -e "${YELLOW}MCP Server is already running on port ${PORT}${NC}"
    exit 0
fi

cd "${SERVICE_DIR}"

# Load environment
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    set -a
    source "${PROJECT_ROOT}/.env"
    set +a
fi

# Determine which server to use
if [[ -f "server_enhanced.py" ]]; then
    START_CMD="python3 server_enhanced.py"
elif [[ -f "server_v2_memory.py" ]]; then
    START_CMD="python3 server_v2_memory.py"
else
    START_CMD="python3 server.py"
fi

# Start service
nohup bash -c "${START_CMD}" > "${LOGS_DIR}/mcp-server.log" 2>&1 &
PID=$!
echo "${PID}" > "${LOGS_DIR}/mcp-server.pid"

sleep 3

if netstat -tlnp 2>/dev/null | grep -q ":${PORT} " || ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
    echo -e "${GREEN}✓ MCP Server started successfully (PID: ${PID})${NC}"
    echo -e "${GREEN}  URL: http://localhost:${PORT}${NC}"
else
    echo -e "${YELLOW}MCP Server starting... Check log: ${LOGS_DIR}/mcp-server.log${NC}"
fi
