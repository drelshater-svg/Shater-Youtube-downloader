#!/bin/bash
echo "==================================================="
echo "  Starting Studio Video Customization Suite"
echo "==================================================="

# Check for uv installation, install if missing
if ! command -v uv &> /dev/null; then
    echo "[INFO] uv manager not found. Installing uv..."
    curl -LsSf https://astral.sh | sh
    source $HOME/.local/bin/env
fi

echo "[INFO] Synchronizing dependencies and running project..."
# Execute the app inside an isolated environment pinned to Python 3.11
uv run --python 3.12 yotube_downloader.py

