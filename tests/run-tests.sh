#!/bin/bash
# ============================================================================
# AI-Assistant Test Runner (Linux/Mac)
# Runs all tests with coverage reporting
# ============================================================================

set -e  # Exit on error

echo "========================================"
echo "AI-Assistant Test Suite"
echo "========================================"
echo ""

# Check if virtual environment exists
if [ ! -f "venv/bin/activate" ]; then
    echo "[ERROR] Virtual environment not found!"
    echo "Please run: python -m venv venv"
    echo "Then: source venv/bin/activate"
    echo "And: pip install -r requirements.txt -r requirements-test.txt"
    exit 1
fi

# Activate virtual environment
echo "[1/5] Activating virtual environment..."
source venv/bin/activate

# Install test dependencies
echo ""
echo "[2/5] Installing test dependencies..."
pip install -q -r requirements-test.txt

# Clear previous coverage data
echo ""
echo "[3/5] Cleaning previous test results..."
rm -f .coverage
rm -rf htmlcov
rm -rf .pytest_cache

# Run tests with coverage
echo ""
echo "[4/5] Running tests..."
echo "========================================"
pytest -v --cov=src --cov=ChatBot/src --cov-report=html --cov-report=term-missing --cov-branch

# Check test results
if [ $? -eq 0 ]; then
    echo ""
    echo "========================================"
    echo "[SUCCESS] All tests passed!"
    echo "========================================"
else
    echo ""
    echo "========================================"
    echo "[WARNING] Some tests failed!"
    echo "========================================"
fi

# Open coverage report (for macOS)
echo ""
echo "[5/5] Coverage report generated"
if [ -f "htmlcov/index.html" ]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open htmlcov/index.html
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        xdg-open htmlcov/index.html 2>/dev/null || echo "Open htmlcov/index.html in your browser"
    fi
    echo "Coverage report: htmlcov/index.html"
else
    echo "Coverage report not found"
fi

echo ""
echo "========================================"
echo "Test run complete!"
echo "========================================"
echo ""
