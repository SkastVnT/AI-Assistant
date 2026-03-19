#!/bin/bash
# ============================================================
# Chatbot Service Rollback Script for Linux/Mac
# ============================================================

set -e

echo ""
echo "========================================"
echo "  Chatbot Service Rollback"
echo "========================================"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
SERVICE_DIR="$PROJECT_ROOT/services/chatbot"
BACKUP_DIR="$PROJECT_ROOT/backups"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# List available backups
echo "Available backups:"
echo "----------------------------------------"

backups=($(ls -t "$BACKUP_DIR"/chatbot_backup_*.tar.gz 2>/dev/null || true))

if [ ${#backups[@]} -eq 0 ]; then
    echo -e "${RED}[ERROR]${NC} No backups found in $BACKUP_DIR"
    exit 1
fi

for i in "${!backups[@]}"; do
    echo "$((i+1)). $(basename "${backups[$i]}")"
done

echo ""
read -p "Enter backup number to restore (or 'q' to quit): " choice

if [ "$choice" == "q" ]; then
    echo "Cancelled."
    exit 0
fi

# Validate choice
if ! [[ "$choice" =~ ^[0-9]+$ ]] || [ "$choice" -lt 1 ] || [ "$choice" -gt ${#backups[@]} ]; then
    echo -e "${RED}[ERROR]${NC} Invalid selection"
    exit 1
fi

selected="${backups[$((choice-1))]}"
echo ""
echo "Selected: $(basename "$selected")"
echo ""
read -p "Are you sure you want to rollback? (y/n): " confirm

if [ "$confirm" != "y" ]; then
    echo "Cancelled."
    exit 0
fi

echo ""
echo "[1/3] Stopping services..."
echo "----------------------------------------"

# Stop Flask if running
pkill -f "python.*app.py" 2>/dev/null || true
pkill -f "gunicorn.*app:app" 2>/dev/null || true
echo -e "${GREEN}[OK]${NC} Services stopped"

echo ""
echo "[2/3] Restoring backup..."
echo "----------------------------------------"

# Backup current state
if [ -d "$SERVICE_DIR/Storage" ]; then
    rm -rf "$SERVICE_DIR/Storage.bak" 2>/dev/null || true
    mv "$SERVICE_DIR/Storage" "$SERVICE_DIR/Storage.bak"
fi

# Extract backup
mkdir -p "$SERVICE_DIR/Storage"
tar -xzf "$selected" -C "$SERVICE_DIR"

if [ -d "$SERVICE_DIR/Storage" ]; then
    echo -e "${GREEN}[OK]${NC} Backup restored"
    rm -rf "$SERVICE_DIR/Storage.bak" 2>/dev/null || true
else
    echo -e "${RED}[ERROR]${NC} Restore failed, reverting..."
    if [ -d "$SERVICE_DIR/Storage.bak" ]; then
        mv "$SERVICE_DIR/Storage.bak" "$SERVICE_DIR/Storage"
    fi
    exit 1
fi

echo ""
echo "[3/3] Verifying restoration..."
echo "----------------------------------------"

cd "$SERVICE_DIR"

# Check Python
PYTHON=${PYTHON:-python3}
$PYTHON -c "from database import ConversationRepository; print('[OK] Database modules loaded')" 2>/dev/null && \
    echo -e "${GREEN}[OK]${NC} System verified" || \
    echo -e "${YELLOW}[WARN]${NC} Could not verify database modules"

echo ""
echo "========================================"
echo "  Rollback Complete!"
echo "========================================"
echo ""
echo "Restored from: $(basename "$selected")"
echo ""
echo "To restart the service:"
echo "  cd $SERVICE_DIR"
echo "  python app.py"
echo ""
