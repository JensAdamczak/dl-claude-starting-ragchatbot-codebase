#\!/bin/bash
# Run all code quality checks
# Usage: ./scripts/quality.sh

set -e

export PATH="$HOME/.local/bin:$PATH"

cd "$(dirname "$0")/.."

echo "=== Code Quality Checks ==="
echo ""

echo "1. Checking code formatting (black)..."
uv run black --check .
echo "   Passed\!"
echo ""

echo "=== All checks passed ==="
