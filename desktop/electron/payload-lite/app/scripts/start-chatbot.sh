#!/bin/bash
# =============================================================================
# Start ChatBot Service
# Port: 5000
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
SERVICE_DIR="${PROJECT_ROOT}/services/chatbot"
LOGS_DIR="${PROJECT_ROOT}/logs"
PORT=5000

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

mkdir -p "${LOGS_DIR}"

echo -e "${GREEN}Starting ChatBot on port ${PORT}...${NC}"

# Check if already running
if netstat -tlnp 2>/dev/null | grep -q ":${PORT} " || ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
    echo -e "${YELLOW}ChatBot is already running on port ${PORT}${NC}"
    exit 0
fi

cd "${SERVICE_DIR}"

# Load environment
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    set -a
    source "${PROJECT_ROOT}/.env"
    set +a
fi

# Use run.py if exists (handles app.py vs app/ conflict)
if [[ -f "run.py" ]]; then
    START_CMD="python3 run.py"
else
    START_CMD="python3 -c \"from app import create_app; app = create_app(); app.run(host='0.0.0.0', port=${PORT})\""
fi

# Start service
nohup bash -c "${START_CMD}" > "${LOGS_DIR}/chatbot.log" 2>&1 &
PID=$!
echo "${PID}" > "${LOGS_DIR}/chatbot.pid"

sleep 3

if netstat -tlnp 2>/dev/null | grep -q ":${PORT} " || ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
    echo -e "${GREEN}✓ ChatBot started successfully (PID: ${PID})${NC}"
    echo -e "${GREEN}  URL: http://localhost:${PORT}${NC}"
    echo -e "${GREEN}  Chat: POST http://localhost:${PORT}/chat${NC}"
else
    echo -e "${YELLOW}ChatBot starting... Check log: ${LOGS_DIR}/chatbot.log${NC}"
fi
