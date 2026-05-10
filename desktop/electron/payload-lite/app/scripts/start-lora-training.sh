#!/bin/bash
# =============================================================================
# Start LoRA Training Web UI
# Port: 7862
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
SERVICE_DIR="${PROJECT_ROOT}/services/lora-training"
LOGS_DIR="${PROJECT_ROOT}/logs"
PORT=7862

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

mkdir -p "${LOGS_DIR}"

echo -e "${GREEN}Starting LoRA Training on port ${PORT}...${NC}"

# Check if already running
if netstat -tlnp 2>/dev/null | grep -q ":${PORT} " || ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
    echo -e "${YELLOW}LoRA Training is already running on port ${PORT}${NC}"
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
nohup python3 webui.py --port ${PORT} > "${LOGS_DIR}/lora-training.log" 2>&1 &
PID=$!
echo "${PID}" > "${LOGS_DIR}/lora-training.pid"

sleep 5

if netstat -tlnp 2>/dev/null | grep -q ":${PORT} " || ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
    echo -e "${GREEN}✓ LoRA Training started successfully (PID: ${PID})${NC}"
    echo -e "${GREEN}  URL: http://localhost:${PORT}${NC}"
else
    echo -e "${YELLOW}LoRA Training starting... Check log: ${LOGS_DIR}/lora-training.log${NC}"
fi
