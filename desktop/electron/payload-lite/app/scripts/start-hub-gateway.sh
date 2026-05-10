#!/bin/bash
# =============================================================================
# Start Hub Gateway Service
# Port: 3000
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
SERVICE_DIR="${PROJECT_ROOT}/services/hub-gateway"
LOGS_DIR="${PROJECT_ROOT}/logs"
PORT=3000

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

mkdir -p "${LOGS_DIR}"

echo -e "${GREEN}Starting Hub Gateway on port ${PORT}...${NC}"

# Check if already running
if netstat -tlnp 2>/dev/null | grep -q ":${PORT} " || ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
    echo -e "${YELLOW}Hub Gateway is already running on port ${PORT}${NC}"
    exit 0
fi

cd "${SERVICE_DIR}"

# Load environment
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    set -a
    source "${PROJECT_ROOT}/.env"
    set +a
fi

# Start service
nohup python3 hub.py > "${LOGS_DIR}/hub-gateway.log" 2>&1 &
PID=$!
echo "${PID}" > "${LOGS_DIR}/hub-gateway.pid"

sleep 2

if netstat -tlnp 2>/dev/null | grep -q ":${PORT} " || ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
    echo -e "${GREEN}✓ Hub Gateway started successfully (PID: ${PID})${NC}"
    echo -e "${GREEN}  URL: http://localhost:${PORT}${NC}"
    echo -e "${GREEN}  Health: http://localhost:${PORT}/health${NC}"
else
    echo -e "${YELLOW}Hub Gateway starting... Check log: ${LOGS_DIR}/hub-gateway.log${NC}"
fi
