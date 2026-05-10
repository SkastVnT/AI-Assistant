#!/bin/bash
# =============================================================================
# Start Text2SQL Service
# Port: 5002
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
SERVICE_DIR="${PROJECT_ROOT}/services/text2sql"
LOGS_DIR="${PROJECT_ROOT}/logs"
PORT=5002

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

mkdir -p "${LOGS_DIR}"

echo -e "${GREEN}Starting Text2SQL on port ${PORT}...${NC}"

# Check if already running
if netstat -tlnp 2>/dev/null | grep -q ":${PORT} " || ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
    echo -e "${YELLOW}Text2SQL is already running on port ${PORT}${NC}"
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
nohup python3 run.py > "${LOGS_DIR}/text2sql.log" 2>&1 &
PID=$!
echo "${PID}" > "${LOGS_DIR}/text2sql.pid"

sleep 3

if netstat -tlnp 2>/dev/null | grep -q ":${PORT} " || ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
    echo -e "${GREEN}✓ Text2SQL started successfully (PID: ${PID})${NC}"
    echo -e "${GREEN}  URL: http://localhost:${PORT}${NC}"
else
    echo -e "${YELLOW}Text2SQL starting... Check log: ${LOGS_DIR}/text2sql.log${NC}"
fi
