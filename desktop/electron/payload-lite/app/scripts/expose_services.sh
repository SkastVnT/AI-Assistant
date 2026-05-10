#!/bin/bash
# =============================================================================
# expose_services.sh - Expose AI-Assistant services publicly via Cloudflared
# Usage: ./scripts/expose_services.sh [service_name] or ./scripts/expose_services.sh all
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Project directories
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOGS_DIR="${PROJECT_ROOT}/logs"

# Service configurations
declare -A SERVICES=(
    ["hub-gateway"]="3000"
    ["chatbot"]="5000"
    ["speech2text"]="5001"
    ["text2sql"]="5002"
    ["document-intelligence"]="5003"
    ["stable-diffusion"]="7860"
    ["lora-training"]="7862"
    ["image-upscale"]="7863"
    ["mcp-server"]="8000"
    ["edit-image"]="7861"
)

# Ensure logs directory exists
mkdir -p "${LOGS_DIR}"

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

find_cloudflared() {
    local cloudflared_bin=""
    
    if command -v cloudflared &> /dev/null; then
        cloudflared_bin="cloudflared"
    elif [[ -f "/opt/instance-tools/bin/cloudflared" ]]; then
        cloudflared_bin="/opt/instance-tools/bin/cloudflared"
    elif [[ -f "/tmp/cloudflared" ]]; then
        cloudflared_bin="/tmp/cloudflared"
    else
        log_warn "cloudflared not found. Installing..."
        curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /tmp/cloudflared
        chmod +x /tmp/cloudflared
        cloudflared_bin="/tmp/cloudflared"
    fi
    
    echo "${cloudflared_bin}"
}

check_port() {
    local port=$1
    if ss -tlnp 2>/dev/null | grep -q ":${port} " || netstat -tlnp 2>/dev/null | grep -q ":${port} "; then
        return 0  # Port is in use (service running)
    else
        return 1  # Port is free
    fi
}

expose_service() {
    local service=$1
    local port=${SERVICES[$service]}
    local log_file="${LOGS_DIR}/cloudflared_${service}.log"
    local pid_file="${LOGS_DIR}/cloudflared_${service}.pid"
    local url_file="${LOGS_DIR}/${service}_public_url.txt"
    
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}Exposing ${service} (port ${port})...${NC}"
    
    # Check if service is running
    if ! check_port "${port}"; then
        log_warn "${service} is not running on port ${port}. Please start it first."
        return 1
    fi
    
    # Kill existing tunnel for this service
    if [[ -f "${pid_file}" ]]; then
        local old_pid=$(cat "${pid_file}")
        if kill -0 "${old_pid}" 2>/dev/null; then
            log_info "Stopping existing tunnel for ${service}..."
            kill "${old_pid}" 2>/dev/null || true
            sleep 2
        fi
    fi
    
    # Get cloudflared binary
    local cloudflared_bin=$(find_cloudflared)
    
    # Start tunnel
    log_info "Starting cloudflared tunnel..."
    nohup "${cloudflared_bin}" tunnel --url "http://localhost:${port}" > "${log_file}" 2>&1 &
    local pid=$!
    echo "${pid}" > "${pid_file}"
    
    # Wait for URL
    log_info "Waiting for tunnel URL..."
    local max_wait=30
    local waited=0
    local public_url=""
    
    while [[ -z "${public_url}" && ${waited} -lt ${max_wait} ]]; do
        sleep 1
        ((waited++))
        public_url=$(grep -o 'https://[^[:space:]]*\.trycloudflare\.com' "${log_file}" 2>/dev/null | head -1)
    done
    
    if [[ -n "${public_url}" ]]; then
        echo "${public_url}" > "${url_file}"
        log_success "${service} exposed at: ${public_url}"
        
        # Update JSON file
        update_urls_json "${service}" "${public_url}"
        
        echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
        return 0
    else
        log_error "Failed to get tunnel URL. Check log: ${log_file}"
        echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
        return 1
    fi
}

update_urls_json() {
    local service=$1
    local url=$2
    local json_file="${LOGS_DIR}/public_urls.json"
    
    # Create or update JSON file
    if [[ -f "${json_file}" ]]; then
        # Update existing file
        python3 -c "
import json
with open('${json_file}', 'r') as f:
    data = json.load(f)
data['${service}'] = '${url}'
with open('${json_file}', 'w') as f:
    json.dump(data, f, indent=2)
" 2>/dev/null || true
    else
        # Create new file
        echo "{\"${service}\": \"${url}\"}" > "${json_file}"
    fi
}

stop_all_tunnels() {
    log_info "Stopping all cloudflared tunnels..."
    pkill -f "cloudflared tunnel" 2>/dev/null || true
    
    # Clean up PID files
    rm -f "${LOGS_DIR}"/cloudflared_*.pid 2>/dev/null || true
    
    log_success "All tunnels stopped"
}

print_summary() {
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}                    PUBLIC URLS SUMMARY${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    for service in "${!SERVICES[@]}"; do
        local url_file="${LOGS_DIR}/${service}_public_url.txt"
        if [[ -f "${url_file}" ]]; then
            local url=$(cat "${url_file}")
            printf "  ${GREEN}●${NC} %-25s → %s\n" "${service}" "${url}"
        fi
    done
    
    echo ""
    echo -e "${YELLOW}  Note: URLs are temporary. For permanent URLs, use named tunnels.${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
}

print_usage() {
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  all         Expose all running services"
    echo "  core        Expose core services (hub-gateway, chatbot)"
    echo "  stop        Stop all tunnels"
    echo "  status      Show current public URLs"
    echo "  <service>   Expose specific service (e.g., hub-gateway, chatbot)"
    echo ""
    echo "Available services:"
    for service in "${!SERVICES[@]}"; do
        echo "  - ${service} (port ${SERVICES[$service]})"
    done
}

# Main
case "${1:-}" in
    "all")
        log_info "Exposing all running services..."
        for service in "${!SERVICES[@]}"; do
            if check_port "${SERVICES[$service]}"; then
                expose_service "${service}"
            else
                log_warn "Skipping ${service} (not running)"
            fi
        done
        print_summary
        ;;
    "core")
        log_info "Exposing core services..."
        for service in "hub-gateway" "chatbot"; do
            expose_service "${service}"
        done
        print_summary
        ;;
    "stop")
        stop_all_tunnels
        ;;
    "status")
        print_summary
        ;;
    "")
        print_usage
        ;;
    *)
        if [[ -n "${SERVICES[$1]}" ]]; then
            expose_service "$1"
            print_summary
        else
            log_error "Unknown service: $1"
            print_usage
            exit 1
        fi
        ;;
esac
