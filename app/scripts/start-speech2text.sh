#!/bin/bash
# =============================================================================
# Start Speech2Text Service
# Port: 5001
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
SERVICE_DIR="${PROJECT_ROOT}/services/speech2text"
LOGS_DIR="${PROJECT_ROOT}/logs"
PORT=5001

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

mkdir -p "${LOGS_DIR}"

echo -e "${GREEN}Starting Speech2Text on port ${PORT}...${NC}"

# Check if already running
if netstat -tlnp 2>/dev/null | grep -q ":${PORT} " || ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
    echo -e "${YELLOW}Speech2Text is already running on port ${PORT}${NC}"
    exit 0
fi

cd "${SERVICE_DIR}"

# Load environment
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    set -a
    source "${PROJECT_ROOT}/.env"
    set +a
fi

# Determine start command
if [[ -f "app/web_ui.py" ]]; then
    START_CMD="python3 app/web_ui.py"
elif [[ -f "app/api/main.py" ]]; then
    START_CMD="python3 -m uvicorn app.api.main:app --host 0.0.0.0 --port ${PORT}"
else
    START_CMD="python3 -m uvicorn app.api.simple_main:app --host 0.0.0.0 --port ${PORT}"
fi

# Start service
nohup bash -c "${START_CMD}" > "${LOGS_DIR}/speech2text.log" 2>&1 &
PID=$!
echo "${PID}" > "${LOGS_DIR}/speech2text.pid"

sleep 3

if netstat -tlnp 2>/dev/null | grep -q ":${PORT} " || ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
    echo -e "${GREEN}✓ Speech2Text started successfully (PID: ${PID})${NC}"
    echo -e "${GREEN}  URL: http://localhost:${PORT}${NC}"
else
    echo -e "${YELLOW}Speech2Text starting... Check log: ${LOGS_DIR}/speech2text.log${NC}"
fi
