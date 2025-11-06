#!/bin/bash
# Check Python syntax across the repository
# This script identifies syntax errors before running security scans

echo "=== Python Syntax Check ==="
echo ""

errors=0
warnings=0

# Find all Python files, excluding common virtual environments and third-party code
while IFS= read -r -d '' file; do
    # Attempt to compile the file
    if ! python -m py_compile "$file" 2>/dev/null; then
        echo "⚠️  SYNTAX ERROR: $file"
        python -m py_compile "$file" 2>&1 | grep -v "^$" | head -3
        echo ""
        warnings=$((warnings + 1))
    fi
done < <(find . -type f -name "*.py" \
    ! -path "*/venv/*" \
    ! -path "*/env/*" \
    ! -path "*/.venv/*" \
    ! -path "*/node_modules/*" \
    ! -path "*/__pycache__/*" \
    -print0)

echo "=== Syntax Check Complete ==="
echo "Files with syntax errors: $warnings"
echo ""

if [ $warnings -gt 0 ]; then
    echo "Note: Files with syntax errors will be skipped during security scanning."
    echo "Consider fixing syntax errors for complete code coverage."
fi

# Don't fail the job - just report warnings
exit 0
