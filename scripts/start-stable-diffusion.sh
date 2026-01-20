#!/bin/bash
# =============================================================================
# Start Stable Diffusion Web UI
# Port: 7860
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
SERVICE_DIR="${PROJECT_ROOT}/services/stable-diffusion"
LOGS_DIR="${PROJECT_ROOT}/logs"
PORT=7860

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

mkdir -p "${LOGS_DIR}"

echo -e "${GREEN}Starting Stable Diffusion on port ${PORT}...${NC}"

# Check if already running
if netstat -tlnp 2>/dev/null | grep -q ":${PORT} " || ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
    echo -e "${YELLOW}Stable Diffusion is already running on port ${PORT}${NC}"
    exit 0
fi

cd "${SERVICE_DIR}"

# Load environment
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    set -a
    source "${PROJECT_ROOT}/.env"
    set +a
fi

# Start service with appropriate flags
nohup python3 launch.py --listen --port ${PORT} --skip-torch-cuda-test > "${LOGS_DIR}/stable-diffusion.log" 2>&1 &
PID=$!
echo "${PID}" > "${LOGS_DIR}/stable-diffusion.pid"

sleep 10

if netstat -tlnp 2>/dev/null | grep -q ":${PORT} " || ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
    echo -e "${GREEN}✓ Stable Diffusion started successfully (PID: ${PID})${NC}"
    echo -e "${GREEN}  URL: http://localhost:${PORT}${NC}"
else
    echo -e "${YELLOW}Stable Diffusion starting (may take a while)... Check log: ${LOGS_DIR}/stable-diffusion.log${NC}"
fi
