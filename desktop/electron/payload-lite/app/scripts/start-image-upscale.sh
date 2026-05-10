#!/bin/bash
# =============================================================================
# Start Image Upscale Service
# Port: 7863
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "${SCRIPT_DIR}")"
SERVICE_DIR="${PROJECT_ROOT}/services/image-upscale"
LOGS_DIR="${PROJECT_ROOT}/logs"
PORT=7863

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

mkdir -p "${LOGS_DIR}"

echo -e "${GREEN}Starting Image Upscale on port ${PORT}...${NC}"

# Check if already running
if netstat -tlnp 2>/dev/null | grep -q ":${PORT} " || ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
    echo -e "${YELLOW}Image Upscale is already running on port ${PORT}${NC}"
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
nohup python3 -m src.upscale_tool.app --port ${PORT} > "${LOGS_DIR}/image-upscale.log" 2>&1 &
PID=$!
echo "${PID}" > "${LOGS_DIR}/image-upscale.pid"

sleep 3

if netstat -tlnp 2>/dev/null | grep -q ":${PORT} " || ss -tlnp 2>/dev/null | grep -q ":${PORT} "; then
    echo -e "${GREEN}✓ Image Upscale started successfully (PID: ${PID})${NC}"
    echo -e "${GREEN}  URL: http://localhost:${PORT}${NC}"
else
    echo -e "${YELLOW}Image Upscale starting... Check log: ${LOGS_DIR}/image-upscale.log${NC}"
fi
