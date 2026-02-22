#\!/bin/bash
# Format all Python files with black
# Usage:
#   ./scripts/format.sh          # Auto-format all files
#   ./scripts/format.sh --check  # Check without modifying (CI mode)

set -e

export PATH="$HOME/.local/bin:$PATH"

cd "$(dirname "$0")/.."

if [ "$1" = "--check" ]; then
    echo "Checking code formatting..."
    uv run black --check .
else
    echo "Formatting code..."
    uv run black .
fi
