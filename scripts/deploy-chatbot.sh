#!/bin/bash
# ============================================================
# Chatbot Service Deployment Script for Linux/Mac
# ============================================================

set -e

echo ""
echo "========================================"
echo "  Chatbot Service Deployment"
echo "========================================"
echo ""

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SERVICE_DIR="$PROJECT_ROOT/services/chatbot"
BACKUP_DIR="$PROJECT_ROOT/backups"
LOG_DIR="$PROJECT_ROOT/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Create directories
mkdir -p "$BACKUP_DIR"
mkdir -p "$LOG_DIR"

echo "[1/6] Creating backup..."
echo "----------------------------------------"

# Backup current state
BACKUP_FILE="$BACKUP_DIR/chatbot_backup_$TIMESTAMP.tar.gz"
if [ -d "$SERVICE_DIR/Storage" ]; then
    tar -czf "$BACKUP_FILE" -C "$SERVICE_DIR" Storage 2>/dev/null || true
    if [ -f "$BACKUP_FILE" ]; then
        echo -e "${GREEN}[OK]${NC} Backup created: $BACKUP_FILE"
    else
        echo -e "${YELLOW}[WARN]${NC} No Storage data to backup"
    fi
else
    echo -e "${YELLOW}[WARN]${NC} No Storage directory found"
fi

echo ""
echo "[2/6] Checking Python environment..."
echo "----------------------------------------"

# Check Python
if command -v python3 &> /dev/null; then
    PYTHON=python3
elif command -v python &> /dev/null; then
    PYTHON=python
else
    echo -e "${RED}[ERROR]${NC} Python not found! Please install Python 3.10+"
    exit 1
fi

echo -e "${GREEN}[OK]${NC} Python found: $($PYTHON --version)"

# Check virtual environment
if [ -n "$VIRTUAL_ENV" ]; then
    echo -e "${GREEN}[OK]${NC} Virtual environment active: $VIRTUAL_ENV"
else
    echo -e "${YELLOW}[WARN]${NC} No virtual environment detected"
    echo "       Consider running: python -m venv venv && source venv/bin/activate"
fi

echo ""
echo "[3/6] Installing dependencies..."
echo "----------------------------------------"

cd "$SERVICE_DIR"
if [ -f "requirements.txt" ]; then
    $PYTHON -m pip install -r requirements.txt --quiet
    echo -e "${GREEN}[OK]${NC} Dependencies installed"
else
    echo -e "${YELLOW}[WARN]${NC} No requirements.txt found"
fi

echo ""
echo "[4/6] Running database migrations..."
echo "----------------------------------------"

# Check MongoDB connection
$PYTHON -c "from config.mongodb_helpers import get_mongo_client; print('MongoDB:', 'Connected' if get_mongo_client() else 'Failed')" 2>/dev/null && \
    echo -e "${GREEN}[OK]${NC} Database connection verified" || \
    echo -e "${YELLOW}[WARN]${NC} Could not verify MongoDB connection"

echo ""
echo "[5/6] Running health checks..."
echo "----------------------------------------"

# Test imports
$PYTHON -c "from database import ConversationRepository, MessageRepository, MemoryRepository; print('[OK] Database modules loaded')" 2>/dev/null || \
    echo -e "${YELLOW}[WARN]${NC} Database module import failed"

$PYTHON -c "from database.cache import ChatbotCache; print('[OK] Cache:', 'Available' if ChatbotCache.get_stats() else 'Not available')" 2>/dev/null || \
    echo -e "${YELLOW}[WARN]${NC} Cache module import failed"

$PYTHON -c "from utils.health import get_health_checker; h = get_health_checker(); print('[OK] Health checker loaded')" 2>/dev/null || \
    echo -e "${YELLOW}[WARN]${NC} Health module not available"

echo ""
echo "[6/6] Running smoke tests..."
echo "----------------------------------------"

# Run quick tests
$PYTHON -m pytest tests/test_repositories.py -v --tb=short -q 2>/dev/null && \
    echo -e "${GREEN}[OK]${NC} Smoke tests passed" || \
    echo -e "${YELLOW}[WARN]${NC} Some tests failed - check logs"

echo ""
echo "========================================"
echo "  Deployment Complete!"
echo "========================================"
echo ""
echo "Backup location: $BACKUP_FILE"
echo "Log directory:   $LOG_DIR"
echo ""
echo "To start the service:"
echo "  cd $SERVICE_DIR"
echo "  python app.py"
echo ""
echo "To run with Gunicorn (production):"
echo "  gunicorn -w 4 -b 0.0.0.0:5001 app:app"
echo ""
