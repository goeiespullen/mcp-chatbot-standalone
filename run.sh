#!/bin/bash
# MCP ChatBot - Terminal Interface
#
# This script starts the MCP ChatBot that connects to the MCP Manager Gateway

cd "$(dirname "$0")"

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not found"
    echo "Install with: sudo apt install python3"
    exit 1
fi

# Check Python version (requires 3.7+)
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 7 ]); then
    echo "❌ Python 3.7+ is required (found Python $PYTHON_VERSION)"
    exit 1
fi

echo "✅ Using Python $PYTHON_VERSION"

# Check if MCP Manager is running on port 8700
if ! nc -z localhost 8700 2>/dev/null; then
    echo ""
    echo "⚠️  WARNING: MCP Manager gateway is not running on port 8700"
    echo ""
    echo "Please start MCP Manager first:"
    echo "  cd /path/to/mcp-manager-standalone"
    echo "  ./run.sh"
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "🚀 Starting MCP ChatBot..."
echo ""

# Run the chatbot
python3 chatbot.py "$@"
