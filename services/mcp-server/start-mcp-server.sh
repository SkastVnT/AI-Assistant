#!/bin/bash
# Start AI-Assistant MCP Server (Linux/Mac)

echo "========================================"
echo "AI-Assistant MCP Server"
echo "========================================"
echo ""

cd "$(dirname "$0")"

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 is not installed!"
    echo "Please install Python 3.8+ first"
    exit 1
fi

# Check MCP package
echo "[INFO] Checking MCP SDK..."
if ! python3 -c "import mcp" &> /dev/null; then
    echo "[WARN] MCP SDK not installed!"
    echo "[INFO] Installing MCP SDK..."
    pip3 install "mcp[cli]"
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to install MCP SDK!"
        exit 1
    fi
fi

echo "[INFO] Starting MCP Server..."
echo ""

# Run server
python3 server.py

if [ $? -ne 0 ]; then
    echo ""
    echo "[ERROR] Server stopped with error!"
    exit 1
fi

echo ""
echo "[INFO] Server stopped."
