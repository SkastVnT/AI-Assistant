#!/bin/bash
# =============================================================================
# AI-Assistant Service Manager v3.0
# Cross-platform service management with public exposure via Cloudflared
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="${PROJECT_ROOT}/scripts"
SERVICES_DIR="${PROJECT_ROOT}/services"
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

# Create logs directory if not exists
mkdir -p "${LOGS_DIR}"

# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

print_banner() {
    clear
    echo -e "${CYAN}"
    cat << "EOF"
================================================================================

     █████╗ ██╗    ███████╗███████╗██████╗ ██╗   ██╗██╗ ██████╗███████╗
    ██╔══██╗██║    ██╔════╝██╔════╝██╔══██╗██║   ██║██║██╔════╝██╔════╝
    ███████║██║    ███████╗█████╗  ██████╔╝██║   ██║██║██║     █████╗  
    ██╔══██║██║    ╚════██║██╔══╝  ██╔══██╗╚██╗ ██╔╝██║██║     ██╔══╝  
    ██║  ██║██║    ███████║███████╗██║  ██║ ╚████╔╝ ██║╚██████╗███████╗
    ╚═╝  ╚═╝╚═╝    ╚══════╝╚══════╝╚═╝  ╚═╝  ╚═══╝  ╚═╝ ╚═════╝╚══════╝

                           Service Manager v3.0
================================================================================
EOF
    echo -e "${NC}"
}

print_menu() {
    echo -e "${WHITE}  [SERVICES]${NC}"
    echo -e "  ${GREEN}1.${NC} Hub Gateway            (Port 3000)"
    echo -e "  ${GREEN}2.${NC} ChatBot                (Port 5000) - Multi-Model AI + SD"
    echo -e "  ${GREEN}3.${NC} Speech2Text            (Port 5001)"
    echo -e "  ${GREEN}4.${NC} Text2SQL               (Port 5002)"
    echo -e "  ${GREEN}5.${NC} Document Intelligence  (Port 5003)"
    echo -e "  ${GREEN}6.${NC} Stable Diffusion       (Port 7860)"
    echo -e "  ${GREEN}7.${NC} LoRA Training          (Port 7862)"
    echo -e "  ${GREEN}8.${NC} Image Upscale          (Port 7863)"
    echo -e "  ${GREEN}9.${NC} MCP Server             (Port 8000)"
    echo -e "  ${GREEN}E.${NC} Edit Image             (Port 7861)"
    echo ""
    echo -e "${WHITE}  [BATCH OPERATIONS]${NC}"
    echo -e "  ${YELLOW}A.${NC} Start ALL Services"
    echo -e "  ${YELLOW}S.${NC} Stop ALL Services"
    echo -e "  ${YELLOW}X.${NC} Expose ALL to Public (Cloudflared)"
    echo ""
    echo -e "${WHITE}  [UTILITIES]${NC}"
    echo -e "  ${PURPLE}P.${NC} Setup All (First Run)"
    echo -e "  ${PURPLE}H.${NC} Health Check All"
    echo -e "  ${PURPLE}T.${NC} Run Tests"
    echo -e "  ${PURPLE}C.${NC} Cleanup Logs/Cache"
    echo -e "  ${PURPLE}G.${NC} Check GPU"
    echo -e "  ${PURPLE}V.${NC} Check Python/Venv"
    echo -e "  ${PURPLE}L.${NC} View Logs"
    echo ""
    echo -e "${WHITE}  [DEPLOYMENT]${NC}"
    echo -e "  ${BLUE}D.${NC} Deploy ChatBot"
    echo -e "  ${BLUE}R.${NC} Rollback ChatBot"
    echo ""
    echo -e "  ${RED}Q.${NC} Quit"
    echo ""
    echo "================================================================================"
}

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

# =============================================================================
# SERVICE MANAGEMENT FUNCTIONS
# =============================================================================

check_port() {
    local port=$1
    if netstat -tlnp 2>/dev/null | grep -q ":${port} " || ss -tlnp 2>/dev/null | grep -q ":${port} "; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

get_pid_on_port() {
    local port=$1
    local pid=$(lsof -t -i:${port} 2>/dev/null | head -1)
    echo "${pid:-none}"
}

start_service() {
    local service=$1
    local port=${SERVICES[$service]}
    local service_dir="${SERVICES_DIR}/${service}"
    
    echo -e "${CYAN}Starting ${service} on port ${port}...${NC}"
    
    # Check if already running
    if check_port "${port}"; then
        log_warn "${service} is already running on port ${port}"
        return 0
    fi
    
    # Check if service directory exists
    if [[ ! -d "${service_dir}" ]]; then
        log_error "Service directory not found: ${service_dir}"
        return 1
    fi
    
    cd "${service_dir}"
    
    # Determine how to start the service
    local start_cmd=""
    
    case "${service}" in
        "hub-gateway")
            start_cmd="python3 hub.py"
            ;;
        "chatbot")
            if [[ -f "run.py" ]]; then
                start_cmd="python3 run.py"
            else
                start_cmd="python3 -c \"from app import create_app; app = create_app(); app.run(host='0.0.0.0', port=${port})\""
            fi
            ;;
        "speech2text")
            if [[ -f "app/web_ui.py" ]]; then
                start_cmd="python3 app/web_ui.py"
            else
                start_cmd="python3 -m uvicorn app.api.main:app --host 0.0.0.0 --port ${port}"
            fi
            ;;
        "text2sql")
            start_cmd="python3 run.py"
            ;;
        "document-intelligence")
            start_cmd="python3 run.py"
            ;;
        "stable-diffusion")
            start_cmd="python3 launch.py --listen --port ${port}"
            ;;
        "lora-training")
            start_cmd="python3 webui.py --port ${port}"
            ;;
        "image-upscale")
            start_cmd="python3 -m src.upscale_tool.app --port ${port}"
            ;;
        "mcp-server")
            start_cmd="python3 server.py"
            ;;
        "edit-image")
            start_cmd="python3 run_grok_ui.py"
            ;;
        *)
            log_error "Unknown service: ${service}"
            return 1
            ;;
    esac
    
    # Start the service in background
    nohup bash -c "${start_cmd}" > "${LOGS_DIR}/${service}.log" 2>&1 &
    local pid=$!
    echo "${pid}" > "${LOGS_DIR}/${service}.pid"
    
    # Wait and verify
    sleep 2
    if check_port "${port}"; then
        log_success "${service} started successfully (PID: ${pid})"
    else
        log_warn "${service} started but port ${port} not yet listening. Check logs: ${LOGS_DIR}/${service}.log"
    fi
    
    cd "${PROJECT_ROOT}"
}

stop_service() {
    local service=$1
    local port=${SERVICES[$service]}
    
    echo -e "${YELLOW}Stopping ${service}...${NC}"
    
    # Try to find PID from file first
    local pid_file="${LOGS_DIR}/${service}.pid"
    if [[ -f "${pid_file}" ]]; then
        local pid=$(cat "${pid_file}")
        if [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null; then
            kill "${pid}" 2>/dev/null || true
            rm -f "${pid_file}"
            log_success "Stopped ${service} (PID: ${pid})"
            return 0
        fi
    fi
    
    # Fallback: find by port
    local pid=$(get_pid_on_port "${port}")
    if [[ "${pid}" != "none" && -n "${pid}" ]]; then
        kill "${pid}" 2>/dev/null || true
        log_success "Stopped process on port ${port} (PID: ${pid})"
    else
        log_info "${service} was not running"
    fi
}

stop_all_services() {
    echo -e "${YELLOW}Stopping all services...${NC}"
    for service in "${!SERVICES[@]}"; do
        stop_service "${service}"
    done
    
    # Also stop any cloudflared tunnels
    pkill -f cloudflared 2>/dev/null || true
    log_success "All services stopped"
}

start_all_services() {
    echo -e "${GREEN}Starting all core services...${NC}"
    
    # Start in order of dependency
    local core_services=("hub-gateway" "chatbot" "mcp-server" "document-intelligence" "text2sql")
    
    for service in "${core_services[@]}"; do
        start_service "${service}"
        sleep 2
    done
    
    echo ""
    log_success "Core services started. Use 'X' to expose them publicly."
}

# =============================================================================
# HEALTH CHECK FUNCTIONS
# =============================================================================

health_check_all() {
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}                    SERVICE HEALTH CHECK${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    local running=0
    local stopped=0
    
    for service in "${!SERVICES[@]}"; do
        local port=${SERVICES[$service]}
        local status_icon=""
        local status_text=""
        
        if check_port "${port}"; then
            status_icon="${GREEN}●${NC}"
            status_text="${GREEN}RUNNING${NC}"
            ((running++))
            
            # Try health endpoint
            local health_url="http://localhost:${port}/health"
            local health_response=$(curl -s --max-time 2 "${health_url}" 2>/dev/null || echo "")
            
            if [[ -n "${health_response}" ]]; then
                status_text="${GREEN}HEALTHY${NC}"
            fi
        else
            status_icon="${RED}○${NC}"
            status_text="${RED}STOPPED${NC}"
            ((stopped++))
        fi
        
        printf "  ${status_icon} %-25s Port %-6s [%b]\n" "${service}" "${port}" "${status_text}"
    done
    
    echo ""
    echo -e "${CYAN}───────────────────────────────────────────────────────────────${NC}"
    echo -e "  Summary: ${GREEN}${running} running${NC}, ${RED}${stopped} stopped${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
}

# =============================================================================
# PUBLIC EXPOSURE (CLOUDFLARED)
# =============================================================================

expose_service() {
    local service=$1
    local port=${SERVICES[$service]}
    local log_file="${LOGS_DIR}/cloudflared_${service}.log"
    
    echo -e "${BLUE}Exposing ${service} (port ${port}) via Cloudflared...${NC}"
    
    # Check if service is running
    if ! check_port "${port}"; then
        log_warn "${service} is not running on port ${port}. Starting it first..."
        start_service "${service}"
        sleep 3
    fi
    
    # Find cloudflared
    local cloudflared_bin=""
    if command -v cloudflared &> /dev/null; then
        cloudflared_bin="cloudflared"
    elif [[ -f "/opt/instance-tools/bin/cloudflared" ]]; then
        cloudflared_bin="/opt/instance-tools/bin/cloudflared"
    else
        log_error "cloudflared not found. Installing..."
        curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o /tmp/cloudflared
        chmod +x /tmp/cloudflared
        cloudflared_bin="/tmp/cloudflared"
    fi
    
    # Start tunnel
    nohup "${cloudflared_bin}" tunnel --url "http://localhost:${port}" > "${log_file}" 2>&1 &
    local pid=$!
    echo "${pid}" > "${LOGS_DIR}/cloudflared_${service}.pid"
    
    # Wait for URL
    sleep 5
    local public_url=$(grep -o 'https://[^[:space:]]*\.trycloudflare\.com' "${log_file}" 2>/dev/null | head -1)
    
    if [[ -n "${public_url}" ]]; then
        log_success "${service} exposed at: ${public_url}"
        echo "${public_url}" > "${LOGS_DIR}/${service}_public_url.txt"
    else
        log_warn "Tunnel started but URL not yet available. Check: ${log_file}"
    fi
}

expose_all_services() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}              EXPOSING SERVICES TO PUBLIC${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    # Kill existing tunnels
    pkill -f cloudflared 2>/dev/null || true
    sleep 2
    
    # Expose core services
    local services_to_expose=("hub-gateway" "chatbot")
    
    for service in "${services_to_expose[@]}"; do
        expose_service "${service}"
        sleep 3
    done
    
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}                    PUBLIC URLS SUMMARY${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    
    for service in "${services_to_expose[@]}"; do
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

# =============================================================================
# SETUP & DEPLOYMENT
# =============================================================================

setup_all() {
    echo -e "${PURPLE}Setting up all services...${NC}"
    
    # Install Python dependencies
    echo -e "${CYAN}Installing Python dependencies...${NC}"
    pip install -r "${PROJECT_ROOT}/requirements.txt" --quiet 2>/dev/null || {
        log_warn "Some dependencies failed. Trying chunks..."
        for chunk in "${PROJECT_ROOT}"/requirements_chunk_*.txt; do
            pip install -r "${chunk}" --quiet 2>/dev/null || true
        done
    }
    
    # Run fix dependencies script
    if [[ -f "${SCRIPTS_DIR}/fix_dependencies.py" ]]; then
        python3 "${SCRIPTS_DIR}/fix_dependencies.py"
    fi
    
    # Create necessary directories
    mkdir -p "${LOGS_DIR}"
    mkdir -p "${PROJECT_ROOT}/app/data/cache"
    
    log_success "Setup complete!"
}

deploy_chatbot() {
    echo -e "${BLUE}Deploying ChatBot service...${NC}"
    
    cd "${SERVICES_DIR}/chatbot"
    
    # Pull latest changes if git repo
    if [[ -d ".git" ]]; then
        git pull origin master 2>/dev/null || true
    fi
    
    # Install/update dependencies
    pip install -r requirements.txt --quiet 2>/dev/null || true
    
    # Restart service
    stop_service "chatbot"
    sleep 2
    start_service "chatbot"
    
    cd "${PROJECT_ROOT}"
    log_success "ChatBot deployed successfully!"
}

rollback_chatbot() {
    echo -e "${YELLOW}Rolling back ChatBot service...${NC}"
    
    cd "${SERVICES_DIR}/chatbot"
    
    if [[ -d ".git" ]]; then
        git checkout HEAD~1 2>/dev/null || {
            log_error "Rollback failed - not a git repository or no previous commit"
            return 1
        }
        
        # Restart service
        stop_service "chatbot"
        sleep 2
        start_service "chatbot"
        
        log_success "ChatBot rolled back to previous version!"
    else
        log_error "Cannot rollback - not a git repository"
    fi
    
    cd "${PROJECT_ROOT}"
}

# =============================================================================
# UTILITIES
# =============================================================================

cleanup_logs() {
    echo -e "${PURPLE}Cleaning up logs and cache...${NC}"
    
    # Clean logs
    find "${LOGS_DIR}" -name "*.log" -mtime +7 -delete 2>/dev/null || true
    find "${LOGS_DIR}" -name "*.pid" -delete 2>/dev/null || true
    
    # Clean Python cache
    find "${PROJECT_ROOT}" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find "${PROJECT_ROOT}" -type f -name "*.pyc" -delete 2>/dev/null || true
    
    # Clean app cache
    rm -rf "${PROJECT_ROOT}/app/data/cache/*" 2>/dev/null || true
    
    log_success "Cleanup complete!"
}

check_gpu() {
    echo -e "${CYAN}Checking GPU status...${NC}"
    echo ""
    
    if command -v nvidia-smi &> /dev/null; then
        nvidia-smi
    else
        echo "NVIDIA GPU not detected or nvidia-smi not available"
        
        # Check for other GPUs
        if [[ -f "/proc/driver/nvidia/version" ]]; then
            cat /proc/driver/nvidia/version
        fi
    fi
    echo ""
}

check_python() {
    echo -e "${CYAN}Checking Python environment...${NC}"
    echo ""
    
    echo "Python version:"
    python3 --version
    echo ""
    
    echo "Python location:"
    which python3
    echo ""
    
    echo "Key packages:"
    pip list 2>/dev/null | grep -E "flask|torch|numpy|transformers|gradio" || echo "Some packages not found"
    echo ""
}

run_tests() {
    echo -e "${CYAN}Running tests...${NC}"
    
    cd "${PROJECT_ROOT}"
    
    if [[ -f "pytest.ini" ]]; then
        python3 -m pytest tests/ -v --tb=short --maxfail=5 2>/dev/null || {
            log_warn "Some tests failed. Check output above."
        }
    else
        log_warn "No pytest.ini found. Running basic tests..."
        python3 -m pytest tests/ -v 2>/dev/null || true
    fi
}

view_logs() {
    echo -e "${CYAN}Available logs:${NC}"
    echo ""
    
    ls -la "${LOGS_DIR}"/*.log 2>/dev/null || echo "No logs found"
    
    echo ""
    echo "Enter service name to view log (or 'q' to go back):"
    read -r service_name
    
    if [[ "${service_name}" != "q" && -f "${LOGS_DIR}/${service_name}.log" ]]; then
        tail -100 "${LOGS_DIR}/${service_name}.log"
    fi
}

# =============================================================================
# MAIN MENU LOOP
# =============================================================================

main() {
    while true; do
        print_banner
        print_menu
        
        echo -n "  Enter choice: "
        read -r choice
        
        case "${choice}" in
            1) start_service "hub-gateway" ;;
            2) start_service "chatbot" ;;
            3) start_service "speech2text" ;;
            4) start_service "text2sql" ;;
            5) start_service "document-intelligence" ;;
            6) start_service "stable-diffusion" ;;
            7) start_service "lora-training" ;;
            8) start_service "image-upscale" ;;
            9) start_service "mcp-server" ;;
            [Ee]) start_service "edit-image" ;;
            [Aa]) start_all_services ;;
            [Ss]) stop_all_services ;;
            [Xx]) expose_all_services ;;
            [Pp]) setup_all ;;
            [Hh]) health_check_all ;;
            [Tt]) run_tests ;;
            [Cc]) cleanup_logs ;;
            [Gg]) check_gpu ;;
            [Vv]) check_python ;;
            [Ll]) view_logs ;;
            [Dd]) deploy_chatbot ;;
            [Rr]) rollback_chatbot ;;
            [Qq]) 
                echo -e "${GREEN}Goodbye!${NC}"
                exit 0
                ;;
            *)
                log_error "Invalid choice: ${choice}"
                ;;
        esac
        
        echo ""
        echo "Press Enter to continue..."
        read -r
    done
}

# Run main function
main "$@"
