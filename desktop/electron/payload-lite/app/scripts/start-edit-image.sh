#!/bin/bash
# =============================================================================
# Start Edit Image (Grok UI) Service
# Port: 7861
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
SERVICE_DIR="${PROJECT_ROOT}/services/edit-image"
LOGS_DIR="${PROJECT_ROOT}/logs"
PORT=7861

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

mkdir -p "${LOGS_DIR}"

echo -e "${GREEN}Starting Edit Image on port ${PORT}...${NC}"

# Check if already running
if netstat -tlnp 2>/dev/null | grep -q ":${PORT} " || ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
    echo -e "${YELLOW}Edit Image is already running on port ${PORT}${NC}"
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
nohup python3 run_grok_ui.py > "${LOGS_DIR}/edit-image.log" 2>&1 &
PID=$!
echo "${PID}" > "${LOGS_DIR}/edit-image.pid"

sleep 5

if netstat -tlnp 2>/dev/null | grep -q ":${PORT} " || ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
    echo -e "${GREEN}✓ Edit Image started successfully (PID: ${PID})${NC}"
    echo -e "${GREEN}  URL: http://localhost:${PORT}${NC}"
else
    echo -e "${YELLOW}Edit Image starting... Check log: ${LOGS_DIR}/edit-image.log${NC}"
fi
