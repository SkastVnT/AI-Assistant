#!/usr/bin/env bash
# Clone/update the last30days-skill engine for AI-Assistant integration.
# Requires: git, Python 3.12+
# Config: ~/.config/last30days/.env (API keys per source — see last30days docs)

set -euo pipefail

BRANCH="${1:-main}"
FORCE="${2:-}"
REPO_URL="https://github.com/mvanhorn/last30days-skill.git"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$SCRIPT_DIR/repo"

echo "[last30days] Setup starting..."

# Clone or update
if [ -d "$REPO_DIR/.git" ]; then
    if [ "$FORCE" = "--force" ]; then
        echo "[last30days] Force update — pulling latest..."
        cd "$REPO_DIR"
        git fetch origin
        git reset --hard "origin/$BRANCH"
        cd "$SCRIPT_DIR"
    else
        echo "[last30days] Repo already exists. Pass --force to update."
    fi
else
    echo "[last30days] Cloning $REPO_URL ..."
    git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$REPO_DIR"
fi

# Verify entry point exists
ENTRY_POINT="$REPO_DIR/scripts/last30days.py"
if [ ! -f "$ENTRY_POINT" ]; then
    echo "[last30days] ERROR: Entry point not found: $ENTRY_POINT" >&2
    exit 1
fi

# Check Python version
if command -v python3 &>/dev/null; then
    echo "[last30days] System Python: $(python3 --version)"
else
    echo "[last30days] WARNING: python3 not found on PATH. Ensure Python 3.12+ is available."
fi

echo "[last30days] Setup complete. Engine at: $REPO_DIR"
echo "[last30days] Configure API keys in: ~/.config/last30days/.env"
