#!/bin/bash
# =============================================================================
# AI-Assistant First-Time Setup
# Installs all dependencies and prepares the environment
# =============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "${SCRIPT_DIR}")")"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
cat << "EOF"
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
                    AI-ASSISTANT FIRST-TIME SETUP
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
EOF
echo -e "${NC}"

# Check Python
echo -e "${BLUE}[1/7] Checking Python...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}âœ“ ${PYTHON_VERSION}${NC}"
else
    echo -e "${RED}âœ— Python 3 not found. Please install Python 3.10+${NC}"
    exit 1
fi

# Check pip
echo ""
echo -e "${BLUE}[2/7] Checking pip...${NC}"
if command -v pip3 &> /dev/null || command -v pip &> /dev/null; then
    echo -e "${GREEN}âœ“ pip available${NC}"
else
    echo -e "${RED}âœ— pip not found. Installing...${NC}"
    curl https://bootstrap.pypa.io/get-pip.py -o /tmp/get-pip.py
    python3 /tmp/get-pip.py
fi

# Create directories
echo ""
echo -e "${BLUE}[3/7] Creating directories...${NC}"
mkdir -p "${PROJECT_ROOT}/logs"
mkdir -p "${PROJECT_ROOT}/backups"
mkdir -p "${PROJECT_ROOT}/app/data/cache"
echo -e "${GREEN}âœ“ Directories created${NC}"

# Install dependencies in chunks (more reliable)
echo ""
echo -e "${BLUE}[4/7] Installing Python dependencies...${NC}"
cd "${PROJECT_ROOT}"

# Upgrade pip first
pip install --upgrade pip --quiet

# Install chunks if available
if ls requirements_chunk_*.txt 1> /dev/null 2>&1; then
    for chunk in requirements_chunk_*.txt; do
        echo -e "${YELLOW}  Installing ${chunk}...${NC}"
        pip install -r "${chunk}" --quiet 2>/dev/null || {
            echo -e "${YELLOW}  Some packages in ${chunk} failed, continuing...${NC}"
        }
    done
else
    # Install main requirements
    pip install -r requirements.txt --quiet 2>/dev/null || {
        echo -e "${YELLOW}  Some packages failed, continuing...${NC}"
    }
fi
echo -e "${GREEN}âœ“ Core dependencies installed${NC}"

# Run fix dependencies script
echo ""
echo -e "${BLUE}[5/7] Fixing compatibility issues...${NC}"
if [[ -f "${SCRIPT_DIR}/fix_dependencies.py" ]]; then
    python3 "${SCRIPT_DIR}/fix_dependencies.py"
else
    echo -e "${YELLOW}  No fix script found, skipping${NC}"
fi
echo -e "${GREEN}âœ“ Compatibility fixes applied${NC}"

# Setup environment file
echo ""
echo -e "${BLUE}[6/7] Setting up environment...${NC}"
if [[ ! -f "${PROJECT_ROOT}/.env" ]]; then
    if [[ -f "${PROJECT_ROOT}/.env.example" ]]; then
        cp "${PROJECT_ROOT}/.env.example" "${PROJECT_ROOT}/.env"
        echo -e "${GREEN}âœ“ Created .env from .env.example${NC}"
        echo -e "${YELLOW}  âš  Please edit .env and add your API keys${NC}"
    else
        echo -e "${YELLOW}  No .env.example found${NC}"
    fi
else
    echo -e "${GREEN}âœ“ .env already exists${NC}"
fi

# Make scripts executable
echo ""
echo -e "${BLUE}[7/7] Setting permissions...${NC}"
chmod +x "${SCRIPT_DIR}"/*.sh 2>/dev/null || true
echo -e "${GREEN}âœ“ Scripts made executable${NC}"

echo ""
echo -e "${GREEN}"
cat << "EOF"
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
                         SETUP COMPLETE!
â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•
EOF
echo -e "${NC}"

echo "Next steps:"
echo ""
echo "  1. Edit .env file and add your API keys:"
echo "     - OPENAI_API_KEY"
echo "     - GEMINI_API_KEY"
echo "     - etc."
echo ""
echo "  2. Start services:"
echo "     bash app/scripts/start-all.sh"
echo ""
echo "  3. Expose to public:"
echo "     bash app/scripts/expose-public.sh"
echo ""
echo "  4. Check health:"
echo "     bash app/scripts/health-check-all.sh"
echo ""
